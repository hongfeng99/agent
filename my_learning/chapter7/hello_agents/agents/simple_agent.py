from typing import Any

from ..agent import Agent
from ..message import Message


class SimpleAgent(Agent):
    """
    最基础的对话 Agent。

    执行流程：
    1. 接收用户输入；
    2. 构造发送给模型的消息；
    3. 调用大模型；
    4. 保存用户消息；
    5. 保存助手回答；
    6. 返回模型回答。
    """

    def run(self, input_text: str, **kwargs: Any) -> str:
        """
        执行一次对话。

        input_text:
            用户当前输入的文本。

        kwargs:
            预留的额外参数。
            后续可以用于临时覆盖 temperature 等配置。

        返回：
            大模型生成的回答字符串。
        """

        if not isinstance(input_text, str):
            raise TypeError("input_text 必须是字符串。")

        if not input_text.strip():
            raise ValueError("input_text 不能为空。")

        # 使用系统提示词、已有历史消息和当前用户输入，
        # 构造大模型 API 所需的消息列表。
        messages = self._build_messages(
            current_input=input_text,
        )

        if self.config.debug:
            print("\n[SimpleAgent 调试信息]")
            print("Agent 名称：", self.name)
            print("发送给模型的消息：")

            for message in messages:
                print(message)

        # 默认读取 Config 中的模型参数。
        # 调用 run() 时也可以临时覆盖。
        temperature = kwargs.get(
            "temperature",
            self.config.temperature,
        )

        max_tokens = kwargs.get(
            "max_tokens",
            self.config.max_tokens,
        )

        response = self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 模型成功回答后，再把本轮对话保存到历史记录。
        self.add_message(
            Message(
                role="user",
                content=input_text,
            )
        )

        self.add_message(
            Message(
                role="assistant",
                content=response,
                metadata={
                    "agent_name": self.name,
                },
            )
        )

        if self.config.debug:
            print("模型回答：")
            print(response)
            print("[调试信息结束]\n")

        return response