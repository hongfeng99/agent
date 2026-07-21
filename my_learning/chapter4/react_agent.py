import re
from typing import Dict, List, Optional, Tuple

from llm_client import HelloAgentsLLM
from tools import ToolExecutor, create_default_tool_executor


REACT_SYSTEM_PROMPT = """
你是一个使用 ReAct 工作方式解决问题的智能体。

你需要交替进行思考和行动：

1. Thought：分析当前应该做什么。
2. Action：选择一个工具，或者结束任务。
3. 工具执行后的结果会作为 Observation 提供给你。
4. 你需要根据 Observation 决定下一步行动。

你必须严格使用以下格式输出：

Thought: 你的分析
Action: 工具名称[工具输入]

当你已经得到最终答案时，必须使用：

Thought: 我已经得到最终答案
Action: Finish[最终答案]

注意：

1. 每次只能输出一个 Thought 和一个 Action。
2. 不要输出 Observation，Observation 由 Python 程序生成。
3. 不要使用 Markdown 代码块。
4. 不要编造工具执行结果。
5. 需要数学计算时，必须调用 Calculator，不要自己心算。
6. 需要查询外部事实、最新信息或不确定的数据时，必须调用 Search。
7. Search 的 Observation 已经包含所需数据时，不要重复搜索。
8. 需要先搜索再计算时，必须先调用 Search，获得数据后再调用 Calculator。
9. 没有获得工具 Observation 前，禁止假装已经知道工具结果。
10. 工具名称必须与可用工具列表中的名称完全一致。
11. 历史中已经存在成功的工具结果时，不要重复调用相同工具。
""".strip()


REACT_USER_PROMPT_TEMPLATE = """
可用工具：

{tools}

用户问题：

{question}

之前的执行历史：

{history}

请根据用户问题和执行历史，输出下一步 Thought 和 Action。
""".strip()


class ReActAgent:
    """
    一个最小可运行的 ReAct 智能体。

    工作流程：

    1. 将问题、工具说明和历史记录发送给大模型；
    2. 解析模型输出的 Thought 和 Action；
    3. 如果 Action 是工具调用，就由 Python 执行工具；
    4. 将工具结果保存为 Observation；
    5. 再次调用模型；
    6. 如果 Action 是 Finish，则返回最终答案。
    """

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_executor: ToolExecutor,
        max_steps: int = 5,
    ):
        self.llm = llm
        self.tool_executor = tool_executor
        self.max_steps = max_steps

        # 保存每一步的 Thought、Action 和 Observation
        self.history: List[Dict[str, str]] = []

    def reset(self) -> None:
        """
        清空上一次任务的历史。

        同一个 Agent 对象处理新问题时，
        不应该把上一次问题的执行记录带进来。
        """

        self.history = []

    def format_history(self) -> str:
        """
        将历史记录转换成适合放进提示词的字符串。
        """

        if not self.history:
            return "暂无执行历史。"

        formatted_records = []

        for index, record in enumerate(self.history, start=1):
            formatted_record = (
                f"步骤 {index}\n"
                f"Thought: {record['thought']}\n"
                f"Action: {record['action']}\n"
                f"Observation: {record['observation']}"
            )

            formatted_records.append(formatted_record)

        return "\n\n".join(formatted_records)

    def build_messages(self, question: str) -> List[Dict[str, str]]:
        """
        构造发送给大模型的 messages。
        """

        tools_description = self.tool_executor.get_available_tools()
        history_text = self.format_history()

        user_prompt = REACT_USER_PROMPT_TEMPLATE.format(
            tools=tools_description,
            question=question,
            history=history_text,
        )

        messages = [
            {
                "role": "system",
                "content": REACT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        return messages

    @staticmethod
    def normalize_action(action_text: str) -> str:
        """
        对 Action 文本进行标准化。

        例如：

        Calculator[1 + 2]
        calculator[1+2]

        标准化以后都变成：

        calculator[1+2]
        """

        without_spaces = re.sub(r"\s+", "", action_text)

        return without_spaces.lower()


    def count_recent_same_actions(self, action_text: str) -> int:
        """
        从历史记录末尾开始，统计同一个 Action
        连续出现了多少次。
        """

        normalized_current_action = self.normalize_action(action_text)

        same_action_count = 0

        for record in reversed(self.history):
            history_action = record["action"]

            normalized_history_action = self.normalize_action(
                history_action
            )

            if normalized_history_action == normalized_current_action:
                same_action_count += 1
            else:
                break

        return same_action_count


    @staticmethod
    def parse_response(
        response_text: str,
    ) -> Optional[Tuple[str, str, str]]:
        """
        解析模型返回的 Thought 和 Action。

        支持以下格式：

        Thought: 需要进行数学计算
        Action: Calculator[(125 * 8) + 50]

        返回：

        (
            "需要进行数学计算",
            "Calculator",
            "(125 * 8) + 50"
        )
        """

        if not response_text:
            return None

        # 提取 Thought：
        # 从 Thought: 后开始，一直提取到 Action: 前面
        thought_match = re.search(
            pattern=(
                r"Thought\s*[:：]\s*"
                r"(.*?)"
                r"(?=\n\s*Action\s*[:：])"
            ),
            string=response_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 提取完整的 Action 行
        action_match = re.search(
            pattern=r"^\s*Action\s*[:：]\s*(.+?)\s*$",
            string=response_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        if not thought_match or not action_match:
            return None

        thought = thought_match.group(1).strip()
        action_content = action_match.group(1).strip()

        # 找到最外层方括号
        left_bracket_index = action_content.find("[")
        right_bracket_index = action_content.rfind("]")

        if left_bracket_index <= 0:
            return None

        if right_bracket_index <= left_bracket_index:
            return None

        # 方括号后不允许再有其他有效内容
        remaining_content = action_content[right_bracket_index + 1:].strip()

        if remaining_content:
            return None

        tool_name = action_content[:left_bracket_index].strip()

        tool_input = action_content[
            left_bracket_index + 1:right_bracket_index
        ].strip()

        # 检查工具名称是否合法
        tool_name_is_valid = re.fullmatch(
            pattern=r"[A-Za-z_][A-Za-z0-9_-]*",
            string=tool_name,
        )

        if not tool_name_is_valid:
            return None

        if not thought:
            return None

        return thought, tool_name, tool_input

    def run(self, question: str) -> str:
        """
        运行完整的 ReAct 循环。
        """

        self.reset()

        print("\n" + "=" * 60)
        print(f"用户问题：{question}")
        print("=" * 60)

        for current_step in range(1, self.max_steps + 1):
            print(f"\n========== ReAct 第 {current_step} 步 ==========")

            # 1. 构造提示词
            messages = self.build_messages(question)

            # 2. 调用大模型
            response_text = self.llm.think(
                messages=messages,
                temperature=0,
            )

            if not response_text:
                return "Agent 运行失败：模型没有返回有效内容。"

            print("\n--- 模型原始输出 ---")
            print(response_text)

            # 3. 解析 Thought 和 Action
            parsed_result = self.parse_response(response_text)

            if parsed_result is None:
                observation = (
                    "模型输出格式错误。"
                    "请严格输出 Thought: ... 和 "
                    "Action: 工具名称[工具输入]。"
                )

                self.history.append(
                    {
                        "thought": "无法从模型输出中解析 Thought",
                        "action": response_text,
                        "observation": observation,
                    }
                )

                print(f"\nObservation: {observation}")
                continue

            thought, tool_name, tool_input = parsed_result

            action_text = f"{tool_name}[{tool_input}]"

            print("\n--- 解析结果 ---")
            print(f"Thought: {thought}")
            print(f"工具名称：{tool_name}")
            print(f"工具输入：{tool_input}")

            # 4. 判断模型是否要结束任务
            if tool_name.lower() == "finish":
                final_answer = tool_input

                print("\n========== Agent 完成任务 ==========")
                print(f"最终答案：{final_answer}")

                return final_answer

            # 检查模型是否连续重复调用同一个工具
            recent_same_action_count = self.count_recent_same_actions(
                action_text
            )

            if recent_same_action_count >= 2:
                observation = (
                    f"检测到重复工具调用：{action_text}。"
                    "这个 Action 已经连续执行过两次，"
                    "请检查已有 Observation，"
                    "不要继续重复调用相同工具。"
                    "请改用其他工具或使用 Finish 返回答案。"
                )

                self.history.append(
                    {
                        "thought": thought,
                        "action": action_text,
                        "observation": observation,
                    }
                )

                print(f"\nObservation: {observation}")

                continue

            # 5. Python 真正执行工具
            observation = self.tool_executor.execute(
                name=tool_name,
                tool_input=tool_input,
            )

            print(f"\nObservation: {observation}")

            # 6. 保存本轮历史
            self.history.append(
                {
                    "thought": thought,
                    "action": action_text,
                    "observation": observation,
                }
            )

        return (
            f"Agent 在 {self.max_steps} 步内没有完成任务。"
            "可能原因包括模型输出格式不稳定、工具选择错误，"
            "或者 Agent 陷入了重复调用。"
        )


def main():
    """
    测试第一个完整的 ReAct Agent。
    """

    try:
        # 创建大模型客户端
        llm = HelloAgentsLLM()

        # 创建默认工具箱，目前只有 Calculator
        tool_executor = create_default_tool_executor()

        # 创建 ReAct Agent
        agent = ReActAgent(
            llm=llm,
            tool_executor=tool_executor,
            max_steps=6,
        )

        # 第一个测试问题
        question = (
            "请先使用 Search 查询珠穆朗玛峰的海拔高度，"
            "然后使用 Calculator 计算这个高度除以2的结果，"
            "最后同时告诉我原始高度和计算结果。"
        )
        
        final_answer = agent.run(question)

        print("\n--- main() 获得的结果 ---")
        print(final_answer)

    except ValueError as error:
        print(f"配置错误：{error}")

    except Exception as error:
        print(f"程序运行失败：{error}")


if __name__ == "__main__":
    main()