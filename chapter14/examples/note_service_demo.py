from chapter14.backend.models import (
    ResearchState,
    ResearchStatus,
    ResearchTask,
    SearchResult,
    TaskStatus,
    TaskSummary,
)
from chapter14.backend.services.note_service import (
    NoteService,
)


def main() -> None:
    """
    演示如何保存研究状态、任务笔记、
    来源列表和最终报告。
    """

    topic = (
        "MCP 协议对智能体开发有什么价值？"
    )

    task = ResearchTask(
        id=1,
        title="MCP 的核心架构",
        intent=(
            "了解 MCP Host、Client "
            "和 Server 的职责"
        ),
        query=(
            "Model Context Protocol "
            "architecture"
        ),
        status=TaskStatus.COMPLETED,
    )

    sources = [
        SearchResult(
            title="MCP Architecture",
            url=(
                "https://example.com/"
                "mcp-architecture"
            ),
            snippet=(
                "MCP 包含 Host、Client "
                "和 Server。"
            ),
        ),
        SearchResult(
            title="Understanding MCP",
            url=(
                "https://example.org/"
                "understanding-mcp"
            ),
            snippet=(
                "MCP Server 可以向模型应用"
                "提供工具和资源。"
            ),
        ),
    ]

    task_summary = TaskSummary(
        task=task,
        summary=(
            "MCP 通过 Host、Client 和 Server "
            "实现模型应用与外部能力之间的"
            "标准化连接。[1][2]"
        ),
        sources=sources,
    )

    state = ResearchState(
        topic=topic,
        tasks=[task],
        summaries=[task_summary],
        status=ResearchStatus.RESEARCHING,
    )

    note_service = NoteService(
        topic=topic,
    )

    state_path = note_service.save_state(
        state
    )

    task_path = (
        note_service.save_task_summary(
            task_summary
        )
    )

    sources_path = (
        note_service.save_sources(
            state.summaries
        )
    )

    report_path = note_service.save_report(
        """
# MCP 协议研究报告

## 摘要

MCP 为大模型应用连接外部工具和数据
提供了标准化协议。

## 结论

MCP 有助于降低工具接入成本，
并提高智能体系统的可扩展性。
"""
    )

    print("=" * 70)
    print("研究资料保存完成")
    print("=" * 70)

    print(
        f"运行编号："
        f"{note_service.run_id}"
    )

    print(
        f"研究目录："
        f"{note_service.note_dir.resolve()}"
    )

    print(
        f"状态文件："
        f"{state_path.resolve()}"
    )

    print(
        f"任务笔记："
        f"{task_path.resolve()}"
    )

    print(
        f"来源文件："
        f"{sources_path.resolve()}"
    )

    print(
        f"最终报告："
        f"{report_path.resolve()}"
    )


if __name__ == "__main__":
    main()