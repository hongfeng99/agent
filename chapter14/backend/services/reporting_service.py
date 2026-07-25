from hello_agents import HelloAgentsLLM

from chapter14.backend.models import (
    TaskSummary,
)
from chapter14.backend.prompts import (
    REPORTER_SYSTEM_PROMPT,
    build_reporting_prompt,
)


class ReportingService:
    """
    最终研究报告生成服务。

    负责：

    1. 接收研究主题和多个子任务总结；
    2. 构建最终报告提示词；
    3. 调用大模型生成 Markdown 报告；
    4. 检查模型返回内容；
    5. 返回最终研究报告。
    """

    def __init__(
        self,
        llm: HelloAgentsLLM,
    ) -> None:
        """
        初始化最终报告服务。

        参数：
            llm:
                用于生成最终报告的大模型客户端。
        """

        self._llm = llm

    def generate(
        self,
        topic: str,
        summaries: list[TaskSummary],
    ) -> str:
        """
        根据多个子任务总结生成最终研究报告。

        参数：
            topic:
                用户最初输入的研究主题。

            summaries:
                已经完成的子任务总结列表。

        返回：
            Markdown 格式的最终研究报告。

        异常：
            ValueError:
                研究主题、子任务总结或模型返回内容为空。

            TypeError:
                模型返回内容不是字符串。

            RuntimeError:
                大模型调用失败。
        """

        reporting_prompt = build_reporting_prompt(
            topic=topic,
            summaries=summaries,
        )

        messages = [
            {
                "role": "system",
                "content": REPORTER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": reporting_prompt,
            },
        ]

        try:
            response_text = self._llm.invoke(
                messages
            )
        except Exception as exc:
            raise RuntimeError(
                "调用最终报告模型失败。"
            ) from exc

        if not isinstance(response_text, str):
            raise TypeError(
                "最终报告模型应当返回字符串，"
                f"实际类型为："
                f"{type(response_text).__name__}"
            )

        report = response_text.strip()

        if not report:
            raise ValueError(
                "最终报告模型返回了空内容。"
            )

        return report