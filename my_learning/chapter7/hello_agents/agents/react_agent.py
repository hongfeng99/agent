import json
import re
from typing import Any, Dict, List, Optional, Tuple

from ..agent import Agent
from ..config import Config
from ..llm import HelloAgentsLLM
from ..message import Message
from ..tools.registry import ToolRegistry


REACT_PROMPT_TEMPLATE = """
你是一个能够思考并使用工具解决问题的智能助手。

## 可用工具

{tools}

## 工作规则

你必须严格按照以下格式回答：

Thought: 分析当前问题，说明下一步应该做什么。
Action: 要执行的动作。

Action 只能使用下面两种格式之一：

1. 调用工具：

工具名称[JSON参数]

例如：

calculator[{{"expression": "(15 + 5) * 3"}}]

2. 返回最终答案：

Finish[最终答案]

## 重要要求

1. 每次回答只能执行一个 Action；
2. 每次回答必须同时包含 Thought 和 Action；
3. 工具参数必须是合法的 JSON 对象，必须使用双引号；
4. 涉及最新信息、当前信息或外部资料时，必须调用 tavily_search；
5. 涉及准确数学计算时，必须调用 calculator；
6. 不得伪造工具执行结果；
7. 工具结果出现错误时，应根据 Observation 修正 Action；
8. 只有获得足够信息后才能使用 Finish；
9. 不要使用 Markdown 代码块包裹 Thought 和 Action。

## 用户问题

{question}

## 当前执行历史

{history}

现在输出本轮的 Thought 和 Action：
"""


class ReActAgent(Agent):
    """
    使用 ReAct 范式工作的 Agent。

    ReAct：
        Reasoning + Acting

    执行流程：
        Thought
            ↓
        Action
            ↓
        执行工具
            ↓
        Observation
            ↓
        继续 Thought
            ↓
        Finish
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: Optional[int] = None,
        prompt_template: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            config=config,
        )

        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError(
                "tool_registry 必须是 ToolRegistry 对象。"
            )

        self.tool_registry = tool_registry

        # 如果创建 Agent 时单独传入 max_steps，
        # 优先使用该值；否则使用 Config 中的值。
        self.max_steps = (
            max_steps
            if max_steps is not None
            else self.config.max_steps
        )

        if self.max_steps <= 0:
            raise ValueError("max_steps 必须大于 0。")

        self.prompt_template = (
            prompt_template
            if prompt_template is not None
            else REACT_PROMPT_TEMPLATE
        )

        # 保存当前一次任务的 ReAct 执行轨迹。
        self.current_trace: List[str] = []

    def run(
        self,
        input_text: str,
        **kwargs: Any,
    ) -> str:
        """
        执行一次完整的 ReAct 循环。
        """

        if not isinstance(input_text, str):
            raise TypeError("input_text 必须是字符串。")

        if not input_text.strip():
            raise ValueError("input_text 不能为空。")

        if len(self.tool_registry) == 0:
            raise ValueError(
                "ReActAgent 至少需要注册一个工具。"
            )

        # 每次运行新任务时，清空上一个任务的执行轨迹。
        self.current_trace = []

        temperature = kwargs.get(
            "temperature",
            self.config.temperature,
        )

        max_tokens = kwargs.get(
            "max_tokens",
            self.config.max_tokens,
        )

        for step in range(1, self.max_steps + 1):
            prompt = self._build_react_prompt(
                question=input_text,
            )

            messages = self._build_messages(
                current_input=prompt,
            )

            if self.config.debug:
                print(f"\n===== ReAct 第 {step} 步 =====")
                print("发送给模型的提示词：")
                print(prompt)

            response_text = self.llm.invoke(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if self.config.debug:
                print("\n模型原始输出：")
                print(response_text)

            try:
                thought, action = self._parse_output(
                    response_text
                )
            except ValueError as error:
                self.current_trace.append(
                    f"Observation: 模型输出格式错误：{error}"
                )
                continue

            self.current_trace.append(
                f"Thought: {thought}"
            )
            self.current_trace.append(
                f"Action: {action}"
            )

            # 判断模型是否已经给出最终答案。
            final_answer = self._parse_finish(action)

            if final_answer is not None:
                self.add_message(
                    Message(
                        role="user",
                        content=input_text,
                    )
                )

                self.add_message(
                    Message(
                        role="assistant",
                        content=final_answer,
                        metadata={
                            "agent_name": self.name,
                            "steps": step,
                            "trace": self.current_trace.copy(),
                        },
                    )
                )

                if self.config.debug:
                    print("\nReAct 最终答案：")
                    print(final_answer)

                return final_answer

            # 不是 Finish，则解析并执行工具。
            try:
                tool_name, parameters = self._parse_tool_action(
                    action
                )

                observation = self.tool_registry.execute(
                    name=tool_name,
                    parameters=parameters,
                )
            except ValueError as error:
                observation = (
                    f"Action 解析失败：{error}"
                )

            self.current_trace.append(
                f"Observation: {observation}"
            )

            if self.config.debug:
                print("\n工具执行结果：")
                print(observation)

        final_answer = (
            f"抱歉，我在 {self.max_steps} 步内"
            "没有完成这个任务。"
        )

        self.add_message(
            Message(
                role="user",
                content=input_text,
            )
        )

        self.add_message(
            Message(
                role="assistant",
                content=final_answer,
                metadata={
                    "agent_name": self.name,
                    "steps": self.max_steps,
                    "trace": self.current_trace.copy(),
                },
            )
        )

        return final_answer
    

    def _build_react_prompt(
        self,
        question: str,
    ) -> str:
        """
        根据用户问题、工具说明和执行历史构造提示词。
        """

        tools_description = (
            self.tool_registry.format_tools_description()
        )

        if self.current_trace:
            history = "\n".join(self.current_trace)
        else:
            history = "暂无执行历史"

        return self.prompt_template.format(
            tools=tools_description,
            question=question,
            history=history,
        )
    

    def _parse_output(
        self,
        response_text: str,
    ) -> Tuple[str, str]:
        """
        从模型回答中提取 Thought 和 Action。

        期望格式：

        Thought: ...
        Action: ...
        """

        if not isinstance(response_text, str):
            raise ValueError("模型输出不是字符串。")

        cleaned_text = response_text.strip()

        # 某些模型可能仍然添加 Markdown 代码块，
        # 这里进行简单清理。
        cleaned_text = cleaned_text.replace(
            "```text",
            "",
        )
        cleaned_text = cleaned_text.replace(
            "```",
            "",
        )
        cleaned_text = cleaned_text.strip()

        thought_match = re.search(
            r"Thought\s*:\s*(.*?)"
            r"(?=\n\s*Action\s*:)",
            cleaned_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        action_match = re.search(
            r"Action\s*:\s*(.+)$",
            cleaned_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if thought_match is None:
            raise ValueError("没有找到 Thought。")

        if action_match is None:
            raise ValueError("没有找到 Action。")

        thought = thought_match.group(1).strip()
        action = action_match.group(1).strip()

        if not thought:
            raise ValueError("Thought 不能为空。")

        if not action:
            raise ValueError("Action 不能为空。")

        return thought, action
    

    def _parse_finish(
        self,
        action: str,
    ) -> Optional[str]:
        """
        判断 Action 是否为 Finish。

        是 Finish 时返回最终答案，
        否则返回 None。
        """

        finish_match = re.fullmatch(
            r"Finish\s*\[(.*)\]",
            action.strip(),
            flags=re.IGNORECASE | re.DOTALL,
        )

        if finish_match is None:
            return None

        final_answer = finish_match.group(1).strip()

        if not final_answer:
            raise ValueError("Finish 中的最终答案不能为空。")

        return final_answer
    

    def _parse_tool_action(
        self,
        action: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        解析工具调用 Action。

        期望格式：

        calculator[{"expression": "15 * 8 + 32"}]
        """

        action_match = re.fullmatch(
            r"([a-zA-Z_][a-zA-Z0-9_-]*)\s*"
            r"\[(.*)\]",
            action.strip(),
            flags=re.DOTALL,
        )

        if action_match is None:
            raise ValueError(
                "工具调用格式错误，正确格式为："
                '工具名[{"参数名": "参数值"}]'
            )

        tool_name = action_match.group(1).strip()
        parameters_text = action_match.group(2).strip()

        if not parameters_text:
            parameters: Dict[str, Any] = {}
        else:
            try:
                parsed_parameters = json.loads(
                    parameters_text
                )
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"工具参数不是合法 JSON：{error.msg}"
                ) from error

            if not isinstance(parsed_parameters, dict):
                raise ValueError(
                    "工具参数必须是 JSON 对象。"
                )

            parameters = parsed_parameters

        return tool_name, parameters