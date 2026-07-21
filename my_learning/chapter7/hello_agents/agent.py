from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .config import Config
from .llm import HelloAgentsLLM
from .message import Message


class Agent(ABC):
    """
    所有 Agent 的抽象基类。

    负责统一管理：

    1. Agent 名称；
    2. 大模型客户端；
    3. 系统提示词；
    4. Agent 配置；
    5. 历史消息；
    6. run() 统一执行接口。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
    ) -> None:
        """
        初始化 Agent。

        name:
            Agent 的名称。

        llm:
            用于调用大模型的 HelloAgentsLLM 对象。

        system_prompt:
            Agent 的系统提示词。

        config:
            Agent 的配置对象。
            没有传入时，自动使用默认 Config。
        """

        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()

        # 保存用户消息和助手消息
        self._history: List[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """
        执行 Agent。

        所有具体 Agent 都必须重写这个方法。

        例如：
        - SimpleAgent 直接调用一次模型；
        - ReActAgent 循环思考并调用工具；
        - ReflectionAgent 生成、反思和改进；
        - PlanAndSolveAgent 先规划再执行。
        """

        raise NotImplementedError

    def add_message(self, message: Message) -> None:
        """
        向历史记录中添加一条消息。
        """

        self._history.append(message)
        self._trim_history()

    def get_history(self) -> List[Message]:
        """
        获取历史消息。

        返回副本，避免外部代码直接修改 Agent 内部的历史记录。
        """

        return self._history.copy()

    def clear_history(self) -> None:
        """
        清空历史消息。
        """

        self._history.clear()

    def _trim_history(self) -> None:
        """
        根据配置限制历史消息数量。

        当历史消息超过 max_history_length 时，
        删除最早的消息，只保留最新的消息。
        """

        max_length = self.config.max_history_length

        if max_length <= 0:
            self._history.clear()
            return

        if len(self._history) > max_length:
            self._history = self._history[-max_length:]

    def _build_messages(
        self,
        current_input: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        构造发送给大模型的消息列表。

        消息顺序：

        1. system 消息；
        2. 历史消息；
        3. 当前用户输入。
        """

        messages: List[Dict[str, str]] = []

        if self.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self.system_prompt,
                }
            )

        for message in self._history:
            messages.append(message.to_dict())

        if current_input is not None:
            messages.append(
                {
                    "role": "user",
                    "content": current_input,
                }
            )

        return messages