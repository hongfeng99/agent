from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

from chapter14.backend.models import (
    ResearchTask,
    SearchResult,
    TaskStatus,
    TaskSummary,
)
from chapter14.backend.services.reporting_service import (
    ReportingService,
)
from chapter14.backend.services.note_service import (
    NoteService,
)

def create_demo_summaries() -> list[TaskSummary]:
    """
    创建用于报告生成演示的子任务总结。

    这里暂时使用固定数据，
    避免重复调用搜索 API 和总结模型。
    """

    architecture_task = ResearchTask(
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

    application_task = ResearchTask(
        id=2,
        title="MCP 的应用价值",
        intent=(
            "分析 MCP 对智能体工具接入"
            "和系统扩展的价值"
        ),
        query=(
            "Model Context Protocol "
            "agent applications"
        ),
        status=TaskStatus.COMPLETED,
    )

    architecture_source = SearchResult(
        title="MCP Architecture",
        url="https://example.com/mcp",
        snippet=(
            "MCP 使用 Host、Client 和 Server "
            "组织模型应用与外部能力之间的连接。"
        ),
    )

    application_source = SearchResult(
        title="MCP Agent Applications",
        url=(
            "https://example.org/"
            "mcp-applications"
        ),
        snippet=(
            "MCP 可以减少不同智能体应用"
            "重复开发工具适配代码的工作。"
        ),
    )

    architecture_summary = TaskSummary(
        task=architecture_task,
        summary="""
## 核心结论

MCP 使用 Host、Client 和 Server 三种核心角色。[1]

## 详细分析

Host 承载大模型应用，Client 负责建立协议连接，
Server 则提供工具、资源或提示词等外部能力。[1]

## 局限性

当前资料没有详细比较不同 MCP 实现的性能差异。
""".strip(),
        sources=[
            architecture_source,
        ],
    )

    application_summary = TaskSummary(
        task=application_task,
        summary="""
## 核心结论

MCP 可以通过统一接口降低工具接入成本。[1]

## 详细分析

在传统实现中，每个智能体应用可能需要单独适配外部服务。
MCP 将外部能力封装为标准服务，有助于提高系统扩展性。[1]

## 局限性

当前资料主要讨论架构价值，
缺少大规模生产环境中的量化数据。
""".strip(),
        sources=[
            application_source,
        ],
    )

    return [
        architecture_summary,
        application_summary,
    ]


def main() -> None:
    """
    使用真实大模型将多个任务总结整合成最终报告。
    """

    load_dotenv()

    topic = (
        "MCP 协议对智能体开发有什么价值？"
    )

    summaries = create_demo_summaries()

    llm = HelloAgentsLLM()

    reporting_service = ReportingService(
        llm=llm,
    )

    print("=" * 70)
    print("Deep Research Agent：最终报告阶段")
    print("=" * 70)
    print(f"研究主题：{topic}")
    print(
        f"子任务总结数量："
        f"{len(summaries)}"
    )
    print()
    print("正在调用大模型生成最终报告……")

    try:
        report = reporting_service.generate(
            topic=topic,
            summaries=summaries,
        )

        note_service = NoteService(
            topic=topic,
        )

        report_path = note_service.save_report(
            report
        )

        print()
        print(
            f"报告已保存到："
            f"{report_path.resolve()}"
        )
        
    except Exception as exc:
        print()
        print("最终报告生成失败。")
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
    print(report)


if __name__ == "__main__":
    main()