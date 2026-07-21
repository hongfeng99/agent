import ast
import re
from typing import Any, List, Optional

from ..agent import Agent
from ..config import Config
from ..llm import HelloAgentsLLM
from ..message import Message


PLAN_PROMPT_TEMPLATE = """
你是一位专业的任务规划专家。

请将用户问题分解成多个简单、清晰、能够依次执行的步骤。

要求：
1. 每个步骤必须是明确的子任务；
2. 步骤之间要有合理的先后顺序；
3. 每个步骤应当能够独立执行；
4. 只制定计划，不要直接解决问题；
5. 不要添加解释或前言；
6. 必须输出 Python 字符串列表；
7. 列表中的每个元素必须是字符串；
8. 最多生成 {max_steps} 个步骤。

用户问题：
{question}

请严格按照下面的格式输出：

["步骤1", "步骤2", "步骤3"]
"""


EXECUTE_PROMPT_TEMPLATE = """
你是一位任务执行专家。

请完成当前步骤，并给出准确、清晰的执行结果。

原始用户问题：
{question}

完整计划：
{plan}

当前需要执行的步骤：
第 {step_number} 步：{current_step}

前面步骤的执行结果：
{previous_results}

要求：
1. 只执行当前步骤；
2. 可以使用前面步骤的结果；
3. 不要提前执行后续步骤；
4. 不要重新制定计划；
5. 回答应当具体、准确；
6. 不确定的信息不要编造。

请输出当前步骤的执行结果。
"""


SUMMARY_PROMPT_TEMPLATE = """
请根据计划和所有步骤的执行结果，回答用户最初的问题。

原始用户问题：
{question}

任务计划：
{plan}

各步骤执行结果：
{step_results}

要求：
1. 综合所有有效结果；
2. 直接回答用户最初的问题；
3. 不要描述内部规划过程；
4. 不要使用“步骤一”“执行器”等内部术语；
5. 删除重复和无关内容；
6. 输出完整、清晰的最终答案。

请输出最终答案。
"""

class PlanAndSolveAgent(Agent):
    """
    使用 Plan-and-Solve 范式工作的 Agent。

    执行流程：

    1. 根据用户问题生成计划；
    2. 将计划解析成字符串列表；
    3. 按顺序执行每个步骤；
    4. 汇总所有步骤结果；
    5. 保存用户问题和最终答案。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        plan_prompt_template: Optional[str] = None,
        execute_prompt_template: Optional[str] = None,
        summary_prompt_template: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            config=config,
        )

        self.plan_prompt_template = (
            plan_prompt_template
            or PLAN_PROMPT_TEMPLATE
        )

        self.execute_prompt_template = (
            execute_prompt_template
            or EXECUTE_PROMPT_TEMPLATE
        )

        self.summary_prompt_template = (
            summary_prompt_template
            or SUMMARY_PROMPT_TEMPLATE
        )

        # 保存最近一次任务的内部执行结果。
        self.last_plan: List[str] = []
        self.last_step_results: List[str] = []
        self.last_final_answer: Optional[str] = None

    def run(
        self,
        input_text: str,
        **kwargs: Any,
    ) -> str:
        """
        执行一次完整的 Plan-and-Solve 流程。
        """

        if not isinstance(input_text, str):
            raise TypeError("input_text 必须是字符串。")

        input_text = input_text.strip()

        if not input_text:
            raise ValueError("input_text 不能为空。")

        temperature = kwargs.get(
            "temperature",
            self.config.temperature,
        )

        max_tokens = kwargs.get(
            "max_tokens",
            self.config.max_tokens,
        )

        # 阶段1：生成计划
        plan = self._create_plan(
            question=input_text,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 再次限制步骤数量，防止模型无视提示词。
        plan = plan[: self.config.max_steps]

        if not plan:
            raise ValueError("模型没有生成有效计划。")

        # 阶段2：按顺序执行每个步骤
        step_results: List[str] = []

        for step_number, current_step in enumerate(
            plan,
            start=1,
        ):
            result = self._execute_step(
                question=input_text,
                plan=plan,
                current_step=current_step,
                step_number=step_number,
                previous_results=step_results,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            step_results.append(result)

        # 阶段3：汇总最终答案
        final_answer = self._summarize_results(
            question=input_text,
            plan=plan,
            step_results=step_results,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        self.last_plan = plan.copy()
        self.last_step_results = step_results.copy()
        self.last_final_answer = final_answer

        # 普通历史中只保存原始问题和最终答案。
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
                    "plan": plan.copy(),
                    "step_results": step_results.copy(),
                },
            )
        )

        if self.config.debug:
            print("\n===== Plan-and-Solve 执行完成 =====")

            print("\n任务计划：")
            for index, step in enumerate(plan, start=1):
                print(f"{index}. {step}")

            print("\n步骤结果：")
            for index, result in enumerate(
                step_results,
                start=1,
            ):
                print(f"\n第 {index} 步结果：")
                print(result)

            print("\n最终答案：")
            print(final_answer)

        return final_answer
    

    def _create_plan(
        self,
        question: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> List[str]:
        """
        调用大模型生成任务计划。
        """

        prompt = self.plan_prompt_template.format(
            question=question,
            max_steps=self.config.max_steps,
        )

        messages = self._build_messages(
            current_input=prompt,
        )

        if self.config.debug:
            print("\n[阶段1：生成任务计划]")
            print(prompt)

        response_text = self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if self.config.debug:
            print("\n模型生成的原始计划：")
            print(response_text)

        return self._parse_plan(response_text)
    


    def _parse_plan(
        self,
        response_text: str,
    ) -> List[str]:
        """
        将模型输出解析成 Python 字符串列表。

        例如：

        ["分析需求", "收集信息", "整理答案"]

        解析后得到：

        [
            "分析需求",
            "收集信息",
            "整理答案",
        ]
        """

        if not isinstance(response_text, str):
            raise ValueError("计划输出必须是字符串。")

        cleaned_text = response_text.strip()

        if not cleaned_text:
            raise ValueError("模型返回的计划为空。")

        # 去除模型可能添加的 Markdown 代码块。
        cleaned_text = re.sub(
            r"^```(?:python)?\s*",
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        )

        cleaned_text = re.sub(
            r"\s*```$",
            "",
            cleaned_text,
        )

        cleaned_text = cleaned_text.strip()

        # 当模型在列表前后添加解释时，
        # 尝试提取第一个完整的中括号区域。
        list_match = re.search(
            r"\[.*\]",
            cleaned_text,
            flags=re.DOTALL,
        )

        if list_match is None:
            raise ValueError(
                "没有找到 Python 列表格式的计划。"
            )

        list_text = list_match.group(0)

        try:
            parsed_plan = ast.literal_eval(list_text)
        except (ValueError, SyntaxError) as error:
            raise ValueError(
                "计划不是合法的 Python 列表。"
            ) from error

        if not isinstance(parsed_plan, list):
            raise ValueError("计划必须是列表。")

        valid_steps: List[str] = []

        for index, step in enumerate(
            parsed_plan,
            start=1,
        ):
            if not isinstance(step, str):
                raise ValueError(
                    f"计划中的第 {index} 个元素不是字符串。"
                )

            cleaned_step = step.strip()

            if not cleaned_step:
                raise ValueError(
                    f"计划中的第 {index} 个步骤为空。"
                )

            valid_steps.append(cleaned_step)

        if not valid_steps:
            raise ValueError("计划中没有有效步骤。")

        return valid_steps
    

    def _execute_step(
        self,
        question: str,
        plan: List[str],
        current_step: str,
        step_number: int,
        previous_results: List[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """
        执行计划中的一个步骤。
        """

        formatted_plan = self._format_plan(plan)

        formatted_previous_results = (
            self._format_step_results(previous_results)
            if previous_results
            else "暂无，这是第一个步骤。"
        )

        prompt = self.execute_prompt_template.format(
            question=question,
            plan=formatted_plan,
            current_step=current_step,
            step_number=step_number,
            previous_results=formatted_previous_results,
        )

        messages = self._build_messages(
            current_input=prompt,
        )

        if self.config.debug:
            print(
                f"\n[阶段2：执行第 {step_number} 步]"
            )
            print(prompt)

        result = self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not isinstance(result, str):
            raise ValueError(
                f"第 {step_number} 步的模型结果不是字符串。"
            )

        result = result.strip()

        if not result:
            raise ValueError(
                f"第 {step_number} 步没有产生结果。"
            )

        return result
    

    def _summarize_results(
        self,
        question: str,
        plan: List[str],
        step_results: List[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """
        汇总所有步骤结果，生成最终答案。
        """

        prompt = self.summary_prompt_template.format(
            question=question,
            plan=self._format_plan(plan),
            step_results=self._format_step_results(
                step_results
            ),
        )

        messages = self._build_messages(
            current_input=prompt,
        )

        if self.config.debug:
            print("\n[阶段3：汇总最终答案]")
            print(prompt)

        final_answer = self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not isinstance(final_answer, str):
            raise ValueError("最终答案不是字符串。")

        final_answer = final_answer.strip()

        if not final_answer:
            raise ValueError("最终答案为空。")

        return final_answer
    


    @staticmethod
    def _format_plan(
        plan: List[str],
    ) -> str:
        """
        将计划列表格式化为带编号的文本。
        """

        return "\n".join(
            f"{index}. {step}"
            for index, step in enumerate(
                plan,
                start=1,
            )
        )

    @staticmethod
    def _format_step_results(
        step_results: List[str],
    ) -> str:
        """
        将步骤结果格式化为带编号的文本。
        """

        return "\n\n".join(
            (
                f"第 {index} 步结果：\n"
                f"{result}"
            )
            for index, result in enumerate(
                step_results,
                start=1,
            )
        )
    


