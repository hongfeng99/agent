from typing import Any

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

from chapter14.backend.agent import (
    DeepResearchAgent,
)
from chapter14.backend.services.planning_service import (
    PlanningService,
)
from chapter14.backend.services.reporting_service import (
    ReportingService,
)
from chapter14.backend.services.search_service import (
    SearchService,
)
from chapter14.backend.services.summarization_service import (
    SummarizationService,
)


def print_event(
    event_type: str,
    message: str,
    data: dict[str, Any],
) -> None:
    """
    在命令行打印 Agent 运行事件。
    """

    print()
    print(
        f"[{event_type}] {message}"
    )

    if event_type == "planning_completed":
        print(
            f"任务数量："
            f"{data.get('task_count')}"
        )

    if event_type == "search_completed":
        print(
            f"搜索结果数量："
            f"{data.get('result_count')}"
        )

    if event_type == "research_completed":
        print(
            f"报告路径："
            f"{data.get('report_path')}"
        )


def main() -> None:
    """
    执行一次完整的 Deep Research 工作流。
    """

    load_dotenv()

    llm = HelloAgentsLLM()

    planner = PlanningService(
        llm=llm,
        min_tasks=3,
        max_tasks=5,
    )

    searcher = SearchService(
        max_results=5,
        max_snippet_chars=1200,
    )

    summarizer = SummarizationService(
        llm=llm,
    )

    reporter = ReportingService(
        llm=llm,
    )

    agent = DeepResearchAgent(
        planner=planner,
        searcher=searcher,
        summarizer=summarizer,
        reporter=reporter,
        event_handler=print_event,
    )

    topic = (
        "MCP 协议对智能体开发有什么价值？"
    )

    print("=" * 70)
    print("Deep Research Agent")
    print("=" * 70)
    print(f"研究主题：{topic}")
    print()
    print("研究任务开始执行……")

    try:
        state = agent.research(
            topic
        )
    except Exception as exc:
        print()
        print("=" * 70)
        print("研究任务失败")
        print("=" * 70)
        print(
            f"异常类型："
            f"{type(exc).__name__}"
        )
        print(f"异常信息：{exc}")
        raise

    print()
    print("=" * 70)
    print("最终研究报告")
    print("=" * 70)
    print()
    print(state.final_report)

    print()
    print("=" * 70)
    print("运行结果")
    print("=" * 70)
    print(
        f"最终状态："
        f"{state.status.value}"
    )
    print(
        f"子任务数量："
        f"{len(state.tasks)}"
    )
    print(
        f"总结数量："
        f"{len(state.summaries)}"
    )
    print(
        f"运行编号："
        f"{agent.last_run_id}"
    )
    print(
        f"研究目录："
        f"{agent.last_note_dir}"
    )
    print(
        f"报告路径："
        f"{agent.last_report_path}"
    )


if __name__ == "__main__":
    main()