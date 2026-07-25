from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

from chapter14.backend.models import ResearchTask
from chapter14.backend.services.search_service import (
    SearchService,
)
from chapter14.backend.services.summarization_service import (
    SummarizationService,
)


def main() -> None:
    """
    执行一次真实搜索，并使用大模型生成任务总结。
    """

    load_dotenv()

    task = ResearchTask(
        id=1,
        title="MCP 的核心架构",
        intent=(
            "了解 MCP Host、Client 和 Server "
            "的职责及其相互关系"
        ),
        query=(
            "Model Context Protocol "
            "host client server architecture"
        ),
    )

    search_service = SearchService(
        max_results=5,
        max_snippet_chars=1200,
    )

    llm = HelloAgentsLLM()

    summarization_service = (
        SummarizationService(
            llm=llm,
        )
    )

    print("=" * 70)
    print("Deep Research Agent：单任务搜索与总结")
    print("=" * 70)

    print(f"任务标题：{task.title}")
    print(f"研究目的：{task.intent}")
    print(f"搜索语句：{task.query}")

    print()
    print("正在搜索资料……")

    search_results = search_service.search(
        task.query
    )

    print(
        f"搜索完成，共获得 "
        f"{len(search_results)} 条资料。"
    )

    for index, result in enumerate(
        search_results,
        start=1,
    ):
        print()
        print("-" * 70)
        print(f"[{index}] {result.title}")
        print(f"URL：{result.url}")
        print(f"摘要：{result.snippet}")

    print()
    print("=" * 70)
    print("正在调用大模型生成任务总结……")
    print("=" * 70)

    task_summary = (
        summarization_service.summarize(
            task=task,
            search_results=search_results,
        )
    )

    print()
    print(task_summary.summary)

    print()
    print("=" * 70)
    print("总结结果信息")
    print("=" * 70)
    print(
        f"任务状态："
        f"{task_summary.task.status.value}"
    )
    print(
        f"资料数量："
        f"{len(task_summary.sources)}"
    )


if __name__ == "__main__":
    main()