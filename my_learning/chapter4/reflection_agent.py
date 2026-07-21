from typing import Any, Dict, List, Optional
from llm_client import HelloAgentsLLM


EXECUTION_PROMPT_TEMPLATE = """
你是一位专业的任务执行专家。

请认真完成用户提出的任务，并生成一份完整的初始答案。

用户任务：
{task}

要求：
1. 直接完成任务；
2. 答案需要清晰、准确、完整；
3. 不要进行自我评价；
4. 不要描述你的思考过程；
5. 只输出可以直接交付给用户的答案。
"""

REFLECTION_PROMPT_TEMPLATE = """
你是一位严格、专业的答案评审专家。

请检查当前答案是否正确、完整、清晰，并提出具体、可执行的改进建议。

用户原始任务：
{task}

当前答案：
{current_answer}

此前的执行与反思轨迹：
{trajectory}

请重点检查：
1. 是否准确完成了用户任务；
2. 是否存在事实、逻辑或计算错误；
3. 是否遗漏了边界条件；
4. 代码是否存在潜在错误；
5. 表达是否清晰、完整；
6. 是否存在可以改进的地方。

要求：
1. 只评价当前答案，不要重新回答用户问题；
2. 明确指出存在的问题；
3. 给出具体的修改建议；
4. 不要给出空泛评价；
5. 如果当前答案已经足够好，请明确输出“无需改进”。
"""



REFINEMENT_PROMPT_TEMPLATE = """
你是一位专业的答案改进专家。

请根据用户原始任务、当前答案和反思反馈，对当前答案进行修改和完善。

用户原始任务：
{task}

当前答案：
{current_answer}

反思反馈：
{reflection_feedback}

此前完整轨迹：
{trajectory}

要求：
1. 根据反思反馈修复当前答案的问题；
2. 保留当前答案中正确、有价值的内容；
3. 直接输出改进后的完整答案；
4. 不要只描述如何修改；
5. 不要输出反思过程；
6. 不要提到“当前答案”“反思反馈”或“修改稿”；
7. 输出内容应当可以直接交付给用户。
"""




class Memory:
    """
    Reflection Agent 使用的短期记忆模块。

    主要保存两类记录：

    1. execution：
       智能体生成的答案、代码或解决方案。

    2. reflection：
       智能体对上一次执行结果的评价和改进意见。
    """

    def __init__(self) -> None:
        """
        初始化一个空列表，用来保存当前任务的执行轨迹。
        """
        self.records: List[Dict[str, Any]] = []

    def add_record(
        self,
        record_type: str,
        content: str,
    ) -> None:
        """
        向记忆中添加一条记录。

        参数：
        record_type：
            记录类型，只允许 execution 或 reflection。

        content：
            具体的执行结果或反思内容。
        """

        allowed_types = {"execution", "reflection"}

        if record_type not in allowed_types:
            raise ValueError(
                "record_type 必须是 execution 或 reflection"
            )

        if not content or not content.strip():
            raise ValueError("记录内容不能为空")

        record = {
            "type": record_type,
            "content": content.strip(),
        }

        self.records.append(record)

    def get_last_execution(self) -> Optional[str]:
        """
        获取最近一次 execution 记录。

        如果还没有 execution 记录，就返回 None。
        """

        for record in reversed(self.records):
            if record["type"] == "execution":
                return str(record["content"])

        return None

    def get_last_reflection(self) -> Optional[str]:
        """
        获取最近一次 reflection 记录。

        如果还没有 reflection 记录，就返回 None。
        """

        for record in reversed(self.records):
            if record["type"] == "reflection":
                return str(record["content"])

        return None

    def get_trajectory(self) -> str:
        """
        将所有执行与反思记录整理成一段文本。

        后续会把这段文本放进大模型的提示词，
        让模型看到此前的执行和改进过程。
        """

        if not self.records:
            return "暂无历史记录。"

        trajectory_parts: List[str] = []

        execution_count = 0
        reflection_count = 0

        for record in self.records:
            record_type = record["type"]
            content = str(record["content"])

            if record_type == "execution":
                execution_count += 1

                trajectory_parts.append(
                    f"第 {execution_count} 次执行结果：\n"
                    f"{content}"
                )

            elif record_type == "reflection":
                reflection_count += 1

                trajectory_parts.append(
                    f"第 {reflection_count} 次反思反馈：\n"
                    f"{content}"
                )

        return "\n\n".join(trajectory_parts)

    def clear(self) -> None:
        """
        清空当前任务的所有记忆。
        """

        self.records.clear()


class ReflectionAgent:
    """
    Reflection 智能体。

    当前版本只实现第一阶段：
    1. 接收用户任务；
    2. 调用模型生成初稿；
    3. 把初稿保存到 Memory。
    """

    def __init__(self, llm_client: HelloAgentsLLM) -> None:
        self.llm_client = llm_client
        self.memory = Memory()

    def execute_task(self, task: str) -> Optional[str]:
        """
        调用大模型执行用户任务，生成一份初稿。
        """

        if not task or not task.strip():
            print("任务不能为空。")
            return None

        prompt = EXECUTION_PROMPT_TEMPLATE.format(
            task=task.strip(),
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        print("\n========== Initial Execution ==========")
        print("正在生成初始答案……")

        response_text: Optional[str] = self.llm_client.think(
            messages=messages,
            temperature=0,
        )

        if not response_text:
            print("初始答案生成失败：模型没有返回内容。")
            return None

        initial_answer = response_text.strip()

        # 将初稿保存为 execution 类型的记忆
        self.memory.add_record(
            record_type="execution",
            content=initial_answer,
        )

        print("\n初始答案：")
        print(initial_answer)

        return initial_answer


    def reflect(self, task: str) -> Optional[str]:
        """
        对最近一次执行结果进行反思。

        反思结果会保存为 reflection 类型的记忆。
        """

        if not task or not task.strip():
            print("反思失败：用户任务不能为空。")
            return None

        current_answer = self.memory.get_last_execution()

        if not current_answer:
            print("反思失败：Memory 中没有可供评价的执行结果。")
            return None

        prompt = REFLECTION_PROMPT_TEMPLATE.format(
            task=task.strip(),
            current_answer=current_answer,
            trajectory=self.memory.get_trajectory(),
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        print("\n========== Reflection ==========")
        print("正在检查初始答案……")

        response_text: Optional[str] = self.llm_client.think(
            messages=messages,
            temperature=0,
        )

        if not response_text:
            print("反思失败：模型没有返回内容。")
            return None

        reflection_feedback = response_text.strip()

        self.memory.add_record(
            record_type="reflection",
            content=reflection_feedback,
        )

        print("\n反思反馈：")
        print(reflection_feedback)

        return reflection_feedback


    def refine(self, task: str) -> Optional[str]:
        """
        根据最近一次反思反馈，改进最近一次执行结果。

        改进后的答案会再次保存为 execution 记录。
        """

        if not task or not task.strip():
            print("改进失败：用户任务不能为空。")
            return None

        current_answer = self.memory.get_last_execution()
        reflection_feedback = self.memory.get_last_reflection()

        if not current_answer:
            print("改进失败：Memory 中没有可供修改的执行结果。")
            return None

        if not reflection_feedback:
            print("改进失败：Memory 中没有反思反馈。")
            return None

        prompt = REFINEMENT_PROMPT_TEMPLATE.format(
            task=task.strip(),
            current_answer=current_answer,
            reflection_feedback=reflection_feedback,
            trajectory=self.memory.get_trajectory(),
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        print("\n========== Refinement ==========")
        print("正在根据反思反馈改进答案……")

        response_text: Optional[str] = self.llm_client.think(
            messages=messages,
            temperature=0,
        )

        if not response_text:
            print("答案改进失败：模型没有返回内容。")
            return None

        refined_answer = response_text.strip()

        self.memory.add_record(
            record_type="execution",
            content=refined_answer,
        )

        print("\n改进后的答案：")
        print(refined_answer)

        return refined_answer


    def should_stop(self, reflection_feedback: str) -> bool:
        """
        根据反思反馈判断是否停止迭代。

        当模型明确表示答案已经足够好时，返回 True。
        """

        if not reflection_feedback:
            return False

        feedback = reflection_feedback.strip().lower()

        stop_keywords = [
            "无需改进",
            "不需要改进",
            "没有需要改进",
            "已经足够好",
            "答案已经完整",
            "no improvement needed",
        ]

        return any(
            keyword in feedback
            for keyword in stop_keywords
        )



    def run_initial(self, task: str) -> Optional[str]:
        """
        执行一个新的 Reflection 任务。

        当前只生成初稿，还不进行反思。
        """

        # 每次开始新任务时清空旧任务记录
        self.memory.clear()

        initial_answer = self.execute_task(task)

        if not initial_answer:
            return None

        print("\n========== Memory Trajectory ==========")
        print(self.memory.get_trajectory())

        return initial_answer

    def run_once(self, task: str) -> Optional[str]:
        """
        执行一次完整的“生成初稿 + 反思”流程。

        当前版本还不会根据反思反馈修改答案。
        """

        # 新任务开始前，清除上一个任务的记录
        self.memory.clear()

        # 第一步：生成初稿
        initial_answer = self.execute_task(task)

        if not initial_answer:
            print("任务终止：初始答案生成失败。")
            return None

        # 第二步：评价初稿
        reflection_feedback = self.reflect(task)

        if not reflection_feedback:
            print("任务终止：反思反馈生成失败。")
            return None

        print("\n========== Memory Trajectory ==========")
        print(self.memory.get_trajectory())

        return reflection_feedback
    


    def run_one_iteration(self, task: str) -> Optional[str]:
        """
        完成一次 Reflection 流程：

        1. 生成初稿；
        2. 对初稿进行反思；
        3. 根据反馈生成改进后的答案。
        """

        if not task or not task.strip():
            print("任务不能为空。")
            return None

        # 每个新任务都使用独立的 Memory
        self.memory.clear()

        # 第一步：生成初稿
        initial_answer = self.execute_task(task)

        if not initial_answer:
            print("任务终止：初始答案生成失败。")
            return None

        # 第二步：反思初稿
        reflection_feedback = self.reflect(task)

        if not reflection_feedback:
            print("任务终止：反思反馈生成失败。")
            return None

        # 第三步：根据反馈改进答案
        refined_answer = self.refine(task)

        if not refined_answer:
            print("任务终止：答案改进失败。")
            return None

        print("\n========== Memory Trajectory ==========")
        print(self.memory.get_trajectory())

        print("\n========== Final Answer ==========")
        print(refined_answer)

        return refined_answer


    def run(
        self,
        task: str,
        max_iterations: int = 3,
    ) -> Optional[str]:
        """
        执行完整的多轮 Reflection 流程。

        参数：
        task：
            用户原始任务。

        max_iterations：
            最大反思次数，防止无限循环。
        """

        if not task or not task.strip():
            print("任务不能为空。")
            return None

        if max_iterations <= 0:
            print("max_iterations 必须大于 0。")
            return None

        task = task.strip()

        # 新任务开始前清空旧轨迹
        self.memory.clear()

        # 第一步：生成初稿
        current_answer = self.execute_task(task)

        if not current_answer:
            print("任务终止：初始答案生成失败。")
            return None

        # 最多进行 max_iterations 轮反思
        for iteration in range(1, max_iterations + 1):
            print(
                f"\n========== Reflection Round "
                f"{iteration}/{max_iterations} =========="
            )

            # 对最新答案进行反思
            reflection_feedback = self.reflect(task)

            if not reflection_feedback:
                print("反思失败，返回当前已有答案。")
                break

            # 判断模型是否认为无需继续改进
            if self.should_stop(reflection_feedback):
                print("\n当前答案已经满足要求，停止迭代。")
                break

            # 如果还可以改进，则生成新版本答案
            refined_answer = self.refine(task)

            if not refined_answer:
                print("答案改进失败，返回当前已有答案。")
                break

            current_answer = refined_answer

        # 从 Memory 中获取最新版本答案
        final_answer = self.memory.get_last_execution()

        if not final_answer:
            print("任务失败：没有得到有效答案。")
            return None

        print("\n========== Complete Trajectory ==========")
        print(self.memory.get_trajectory())

        print("\n========== Final Answer ==========")
        print(final_answer)

        return final_answer


def main() -> None:
    llm_client = HelloAgentsLLM()

    agent = ReflectionAgent(llm_client)

    task = (
        "请用 Python 编写一个判断整数是否为质数的函数，"
        "要求包含类型标注、文档字符串和测试示例，"
        "并简要说明实现思路。"
    )

    final_answer = agent.run(
        task=task,
        max_iterations=3,
    )

    print("\n程序最终返回值：")
    print(final_answer)


if __name__ == "__main__":
    main()