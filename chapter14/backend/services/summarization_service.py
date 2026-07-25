from hello_agents import HelloAgentsLLM

from chapter14.backend.models import (
    ResearchTask,
    SearchResult,
    TaskStatus,
    TaskSummary,
)
from chapter14.backend.prompts import (
    SUMMARIZER_SYSTEM_PROMPT,
    build_summarization_prompt,
)


class SummarizationService:
    """
    单个研究子任务的总结服务。

    负责：

    1. 接收研究子任务和搜索资料；
    2. 构建总结提示词；
    3. 调用大模型；
    4. 检查模型返回内容；
    5. 返回 TaskSummary。
    """

    def __init__(
        self,
        llm: HelloAgentsLLM,
    ) -> None:
        """
        初始化总结服务。

        参数：
            llm:
                用于生成研究总结的大模型客户端。
        """

        self._llm = llm

    def summarize(
        self,
        task: ResearchTask,
        search_results: list[SearchResult],
    ) -> TaskSummary:
        """
        根据研究任务和搜索结果生成总结。

        参数：
            task:
                当前研究子任务。

            search_results:
                与该子任务相关的搜索结果。

        返回：
            包含研究总结和来源的 TaskSummary。

        异常：
            ValueError:
                搜索结果为空，或者模型返回空内容。

            TypeError:
                模型返回的内容不是字符串。

            RuntimeError:
                调用大模型失败。
        """

        summarization_prompt = (
            build_summarization_prompt(
                task=task,
                search_results=search_results,
            )
        )

        messages = [
            {
                "role": "system",
                "content": SUMMARIZER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": summarization_prompt,
            },
        ]

        try:
            response_text = self._llm.invoke(
                messages
            )
        except Exception as exc:
            raise RuntimeError(
                "调用任务总结模型失败。"
            ) from exc

        if not isinstance(response_text, str):
            raise TypeError(
                "任务总结模型应当返回字符串，"
                f"实际类型为："
                f"{type(response_text).__name__}"
            )

        summary_text = response_text.strip()

        if not summary_text:
            raise ValueError(
                "任务总结模型返回了空内容。"
            )

        completed_task = task.model_copy(
            update={
                "status": TaskStatus.COMPLETED,
            }
        )

        return TaskSummary(
            task=completed_task,
            summary=summary_text,
            sources=search_results,
        )