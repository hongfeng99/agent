from typing import Any, Dict, List, Optional


class FakeLLM:
    """
    用于测试的假大模型。

    它不会调用真实 API，而是按照顺序返回
    responses 中预先准备好的字符串。
    """

    def __init__(
        self,
        responses: Optional[List[str]] = None,
    ) -> None:
        self.responses = list(responses or [])
        self.calls: List[Dict[str, Any]] = []

    def invoke(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        模拟 HelloAgentsLLM.invoke()。
        """

        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )

        if not self.responses:
            raise RuntimeError(
                "FakeLLM 没有剩余的预设回答。"
            )

        return self.responses.pop(0)