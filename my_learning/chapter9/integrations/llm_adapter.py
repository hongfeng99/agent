from typing import Any, Literal


class RealLLMAdapter:
    """
    将已有的大模型客户端适配为：

        invoke(prompt: str) -> str

    CodebaseMaintainer 只依赖这个统一接口。

    method_name:
        现有客户端调用模型的方法名，例如 invoke 或 chat。

    input_mode:
        text：
            直接把完整上下文字符串传给模型。

        messages：
            将上下文包装成消息列表后传给模型。
    """

    def __init__(
        self,
        llm_client: Any,
        method_name: str = "invoke",
        input_mode: Literal[
            "text",
            "messages",
        ] = "text",
    ) -> None:
        if input_mode not in {
            "text",
            "messages",
        }:
            raise ValueError(
                "input_mode 必须是 text 或 messages。"
            )

        method = getattr(
            llm_client,
            method_name,
            None,
        )

        if not callable(method):
            raise TypeError(
                f"大模型客户端没有可调用的 "
                f"{method_name}() 方法。"
            )

        self.llm_client = llm_client
        self.method_name = method_name
        self.input_mode = input_mode

    def invoke(
        self,
        prompt: str,
    ) -> str:
        """
        调用真实大模型，并统一提取文本回答。
        """

        if not isinstance(prompt, str):
            raise TypeError(
                "prompt 必须是字符串。"
            )

        prompt = prompt.strip()

        if not prompt:
            raise ValueError(
                "prompt 不能为空。"
            )

        method = getattr(
            self.llm_client,
            self.method_name,
        )

        if self.input_mode == "text":
            payload: Any = prompt
        else:
            payload = [
                {
                    "role": "system",
                    "content": prompt,
                }
            ]

        result = method(payload)

        return self._extract_text(result)

    def _extract_text(
        self,
        result: Any,
    ) -> str:
        """
        从不同形式的大模型返回值中提取文本。
        """

        if result is None:
            raise ValueError(
                "大模型没有返回回答，结果为 None。"
                "请检查 API 配置或 llm_client.py 中的异常信息。"
            )

        if isinstance(result, str):
            text = result

        elif isinstance(result, dict):
            text = (
                result.get("content")
                or result.get("text")
                or result.get("answer")
                or ""
            )

        else:
            content = getattr(
                result,
                "content",
                None,
            )

            if isinstance(content, str):
                text = content
            else:
                text = self._extract_from_choices(
                    result
                )

        if not isinstance(text, str):
            text = str(text)

        text = text.strip()

        if not text:
            raise ValueError(
                "大模型返回了空回答。"
            )

        return text

    def _extract_from_choices(
        self,
        result: Any,
    ) -> str:
        """
        尝试兼容带 choices 的模型返回对象。
        """

        choices = getattr(
            result,
            "choices",
            None,
        )

        if not choices:
            return str(result)

        first_choice = choices[0]

        message = getattr(
            first_choice,
            "message",
            None,
        )

        if message is not None:
            content = getattr(
                message,
                "content",
                None,
            )

            if isinstance(content, str):
                return content

        text = getattr(
            first_choice,
            "text",
            None,
        )

        if isinstance(text, str):
            return text

        return str(result)