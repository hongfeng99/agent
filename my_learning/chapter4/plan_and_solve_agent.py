import ast
import re
from typing import Optional

from llm_client import HelloAgentsLLM


PLANNER_PROMPT_TEMPLATE = """
你是一位专业的任务规划专家。

请将用户的问题分解成多个简单、清晰、能够依次执行的步骤。

要求：
1. 每个步骤都必须是明确的子任务；
2. 步骤之间要有合理的先后顺序；
3. 只制定计划，不要直接解决问题；
4. 不要解释计划；
5. 必须输出 Python 列表；
6. 列表中的每个元素必须是字符串。

用户问题：
{question}

请严格按照下面的格式输出：

```python
["步骤1", "步骤2", "步骤3"]
```
"""


EXECUTOR_PROMPT_TEMPLATE = """
你是一位专业的任务执行专家。

请根据原始问题和完整行动计划，只执行当前指定的步骤。

原始问题：
{question}

完整行动计划：
{plan}

当前需要执行的步骤：
{current_step}

此前步骤及其结果：
{previous_results}

要求：
1. 只完成当前步骤；
2. 可以使用此前步骤的结果；
3. 不要跳过当前步骤；
4. 不要重新制定计划；
5. 给出清晰、准确、简洁的执行结果。
"""


FINAL_ANSWER_PROMPT_TEMPLATE = """
你是一位答案整理专家。

请根据用户的原始问题、完整行动计划以及每一步的执行结果，
生成一个完整、准确、简洁的最终答案。

原始问题：
{question}

完整行动计划：
{plan}

所有步骤的执行结果：
{execution_results}

要求：
1. 直接回答用户的原始问题；
2. 综合所有步骤的执行结果；
3. 不要重新制定计划；
4. 不要遗漏关键计算过程；
5. 不要提到“Planner”“Executor”或“执行轨迹”；
6. 如果执行结果之间存在冲突，需要明确指出。
"""


def parse_plan(response_text: str) -> list[str]:
    """
    将模型返回的文本解析成 Python 字符串列表。

    例如模型返回：

    ```python
    ["计算周二销量", "计算周三销量", "计算总销量"]
    ```

    解析后得到：

    [
        "计算周二销量",
        "计算周三销量",
        "计算总销量",
    ]
    """

    # 模型没有返回内容时，直接返回空列表
    if not response_text or not response_text.strip():
        return []

    text = response_text.strip()

    # 尝试提取 Markdown 代码块中的内容
    code_block_match = re.search(
        r"```(?:python)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if code_block_match:
        # 如果找到了代码块，只取代码块内部的内容
        plan_text = code_block_match.group(1).strip()
    else:
        # 如果模型没有使用代码块，就尝试解析整个输出
        plan_text = text

    try:
        # 把列表形式的字符串转换为真正的 Python 列表
        parsed_plan = ast.literal_eval(plan_text)
    except (ValueError, SyntaxError):
        return []

    # 模型输出必须是列表
    if not isinstance(parsed_plan, list):
        return []

    cleaned_plan: list[str] = []

    for item in parsed_plan:
        # 只保留字符串类型的步骤
        if not isinstance(item, str):
            continue

        step = item.strip()

        # 去掉空字符串
        if step:
            cleaned_plan.append(step)

    return cleaned_plan


class Planner:
    """
    Plan-and-Solve 中的规划器。

    Planner 负责：
    1. 接收用户问题；
    2. 构造规划提示词；
    3. 调用大模型；
    4. 将模型输出解析为计划列表。
    """

    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        """
        根据用户问题生成行动计划。
        """

        if not question or not question.strip():
            print("生成计划失败：用户问题不能为空。")
            return []

        prompt = PLANNER_PROMPT_TEMPLATE.format(
            question=question.strip(),
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        print("\n========== Planning Phase ==========")
        print("正在调用大模型生成行动计划……")

        response_text: Optional[str] = self.llm_client.think(
            messages=messages,
            temperature=0,
        )

        if not response_text:
            print("生成计划失败：模型没有返回内容。")
            return []

        print("\n模型原始输出：")
        print(response_text)

        plan = parse_plan(response_text)

        if not plan:
            print("\n计划解析失败。")
            return []

        print("\n解析后的行动计划：")

        for index, step in enumerate(plan, start=1):
            print(f"{index}. {step}")

        return plan


class Executor:
    """
    Plan-and-Solve 中的执行器。

    Executor 负责：
    1. 接收原始问题；
    2. 查看完整计划；
    3. 执行当前步骤；
    4. 参考此前步骤的结果；
    5. 返回当前步骤的执行结果。
    """

    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def execute_step(
        self,
        question: str,
        plan: list[str],
        current_step: str,
        previous_results: list[str],
    ) -> Optional[str]:
        """
        执行计划中的一个步骤。
        """

        # 把完整计划转换为适合放入提示词的文本
        plan_text = "\n".join(
            f"{index}. {step}"
            for index, step in enumerate(plan, start=1)
        )

        # 把此前执行过的步骤和结果组合起来
        if previous_results:
            history_parts = []

            for index, result in enumerate(previous_results):
                previous_step = plan[index]

                history_parts.append(
                    f"步骤 {index + 1}：{previous_step}\n"
                    f"执行结果：{result}"
                )

            previous_results_text = "\n\n".join(history_parts)
        else:
            previous_results_text = "暂无，这是第一个执行步骤。"

        prompt = EXECUTOR_PROMPT_TEMPLATE.format(
            question=question,
            plan=plan_text,
            current_step=current_step,
            previous_results=previous_results_text,
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        response_text: Optional[str] = self.llm_client.think(
            messages=messages,
            temperature=0,
        )

        if not response_text:
            return None

        return response_text.strip()
    


class AnswerSynthesizer:
    """
    最终答案综合器。

    负责读取：
    1. 用户原始问题；
    2. 完整行动计划；
    3. 每一步的执行结果；

    然后生成适合直接返回给用户的最终答案。
    """

    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def synthesize(
        self,
        question: str,
        plan: list[str],
        results: list[str],
    ) -> Optional[str]:
        """
        综合所有步骤的结果，生成最终答案。
        """

        if not results:
            return None

        plan_text = "\n".join(
            f"{index}. {step}"
            for index, step in enumerate(plan, start=1)
        )

        execution_parts = []

        for index, result in enumerate(results):
            execution_parts.append(
                f"步骤 {index + 1}：{plan[index]}\n"
                f"执行结果：{result}"
            )

        execution_results_text = "\n\n".join(execution_parts)

        prompt = FINAL_ANSWER_PROMPT_TEMPLATE.format(
            question=question,
            plan=plan_text,
            execution_results=execution_results_text,
        )

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        response_text: Optional[str] = self.llm_client.think(
            messages=messages,
            temperature=0,
        )

        if not response_text:
            return None

        return response_text.strip()



class PlanAndSolveAgent:
    """
    Plan-and-Solve 智能体总控制器。

    它负责把 Planner 和 Executor 串联起来。
    """

    def __init__(self, llm_client: HelloAgentsLLM):
        self.planner = Planner(llm_client)
        self.executor = Executor(llm_client)

    def run(self, question: str) -> Optional[str]:
        """
        完整执行 Plan-and-Solve 流程。
        """

        # 第一阶段：生成计划
        plan = self.planner.plan(question)

        if not plan:
            print("任务终止：没有生成有效计划。")
            return None

        # 用来保存每个步骤的执行结果
        results: list[str] = []

        print("\n========== Solving Phase ==========")

        # 第二阶段：按照计划顺序执行
        for index, current_step in enumerate(plan, start=1):
            print(f"\n正在执行步骤 {index}/{len(plan)}")
            print(f"当前步骤：{current_step}")

            result = self.executor.execute_step(
                question=question,
                plan=plan,
                current_step=current_step,
                previous_results=results,
            )

            if not result:
                print(f"步骤 {index} 执行失败，任务终止。")
                return None

            # 保存当前步骤的结果
            results.append(result)

            print("当前步骤执行结果：")
            print(result)

        # 最后一个步骤的结果作为最终答案
        final_answer = results[-1]

        print("\n========== Final Answer ==========")
        print(final_answer)

        return final_answer
    

def main() -> None:
    llm_client = HelloAgentsLLM()

    agent = PlanAndSolveAgent(llm_client)

    # question = (
    #     "一个水果店周一卖出了15个苹果，"
    #     "周二卖出的苹果数量是周一的两倍，"
    #     "周三卖出的数量比周二少5个。"
    #     "请问这三天总共卖出了多少个苹果？"
    # )

    # question = (
    #     "小明买了3本书，每本书25元，又买了2支笔，"
    #     "每支笔6元。他支付100元，应找回多少钱？"
    # )

    question = (
        "我每天可以学习2小时，希望在7天内学习Python函数、"
        "类和异常处理。请制定并说明一个合理的学习安排。"
    )

    final_answer = agent.run(question)

    print("\n程序返回的最终结果：")
    print(final_answer)


if __name__ == "__main__":
    main()