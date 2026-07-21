from typing import Any, Optional

from ..agent import Agent
from ..config import Config
from ..llm import HelloAgentsLLM
from ..message import Message


INITIAL_PROMPT_TEMPLATE = """
请认真回答下面的问题。

要求：
1. 回答准确、清晰；
2. 不要编造不确定的信息；
3. 给出必要的解释；
4. 直接回答问题。

用户问题：
{question}
"""


REFLECTION_PROMPT_TEMPLATE = """
你是一位严格的答案审查专家。

请检查下面的初始答案，分析它是否存在问题。

重点检查：
1. 是否正确回答了用户问题；
2. 是否存在事实错误或逻辑错误；
3. 是否遗漏了重要内容；
4. 是否存在表达不清或结构混乱；
5. 是否包含没有依据的结论；
6. 是否可以进一步改进。

用户问题：
{question}

初始答案：
{initial_answer}

请输出具体的审查意见。
不要直接重写答案。
"""


REFINE_PROMPT_TEMPLATE = """
请根据审查意见，改进下面的初始答案。

要求：
1. 修正审查意见指出的问题；
2. 保留初始答案中正确的内容；
3. 补充必要但缺失的信息；
4. 删除重复、错误或无关内容；
5. 输出完整的最终答案；
6. 不要描述修改过程；
7. 不要提到“初始答案”或“审查意见”。

用户问题：
{question}

初始答案：
{initial_answer}

审查意见：
{reflection}

请输出改进后的最终答案。
"""


class ReflectionAgent(Agent):
    """
    使用 Reflection 范式工作的 Agent。

    执行流程：

    1. 生成初始答案；
    2. 反思和检查初始答案；
    3. 根据反思结果生成改进答案；
    4. 保存用户问题和最终答案；
    5. 返回最终答案。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        initial_prompt_template: Optional[str] = None,
        reflection_prompt_template: Optional[str] = None,
        refine_prompt_template: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            config=config,
        )

        self.initial_prompt_template = (
            initial_prompt_template
            or INITIAL_PROMPT_TEMPLATE
        )

        self.reflection_prompt_template = (
            reflection_prompt_template
            or REFLECTION_PROMPT_TEMPLATE
        )

        self.refine_prompt_template = (
            refine_prompt_template
            or REFINE_PROMPT_TEMPLATE
        )

        # 保存最近一次任务的中间结果，
        # 方便调试和查看执行过程。
        self.last_initial_answer: Optional[str] = None
        self.last_reflection: Optional[str] = None
        self.last_final_answer: Optional[str] = None

    def run(
        self,
        input_text: str,
        **kwargs: Any,
    ) -> str:
        """
        执行一次完整的 Reflection 流程。
        """

        if not isinstance(input_text, str):
            raise TypeError("input_text 必须是字符串。")

        if not input_text.strip():
            raise ValueError("input_text 不能为空。")

        temperature = kwargs.get(
            "temperature",
            self.config.temperature,
        )

        max_tokens = kwargs.get(
            "max_tokens",
            self.config.max_tokens,
        )

        initial_answer = self._generate_initial(
            question=input_text,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        reflection = self._reflect(
            question=input_text,
            initial_answer=initial_answer,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        final_answer = self._refine(
            question=input_text,
            initial_answer=initial_answer,
            reflection=reflection,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        self.last_initial_answer = initial_answer
        self.last_reflection = reflection
        self.last_final_answer = final_answer

        # 只把用户问题和最终答案保存到长期历史。
        # 中间草稿和反思结果不写入普通对话历史。
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
                    "initial_answer": initial_answer,
                    "reflection": reflection,
                },
            )
        )

        if self.config.debug:
            print("\n===== Reflection 执行结果 =====")

            print("\n初始答案：")
            print(initial_answer)

            print("\n反思意见：")
            print(reflection)

            print("\n最终答案：")
            print(final_answer)

            print("\n===== Reflection 执行结束 =====")

        return final_answer
    

    def _generate_initial(
        self,
        question: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """
        生成初始答案。
        """

        prompt = self.initial_prompt_template.format(
            question=question,
        )

        messages = self._build_messages(
            current_input=prompt,
        )

        if self.config.debug:
            print("\n[阶段1：生成初始答案]")
            print(prompt)

        return self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    

    def _reflect(
        self,
        question: str,
        initial_answer: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """
        检查初始答案，生成反思意见。
        """

        prompt = self.reflection_prompt_template.format(
            question=question,
            initial_answer=initial_answer,
        )

        messages = self._build_messages(
            current_input=prompt,
        )

        if self.config.debug:
            print("\n[阶段2：反思初始答案]")
            print(prompt)

        return self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    

    def _refine(
        self,
        question: str,
        initial_answer: str,
        reflection: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """
        根据反思意见生成最终答案。
        """

        prompt = self.refine_prompt_template.format(
            question=question,
            initial_answer=initial_answer,
            reflection=reflection,
        )

        messages = self._build_messages(
            current_input=prompt,
        )

        if self.config.debug:
            print("\n[阶段3：生成改进答案]")
            print(prompt)

        return self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )