from chapter14.backend.models import (
    ResearchState,
    ResearchTask,
)


def main() -> None:
    """
    演示研究状态和研究子任务模型。
    """

    topic = "MCP 协议对智能体开发有什么价值？"

    tasks = [
        ResearchTask(
            id=1,
            title="MCP 的基本概念",
            intent="了解 MCP 的设计目标和核心架构",
            query="Model Context Protocol architecture overview",
        ),
        ResearchTask(
            id=2,
            title="MCP 与函数调用的区别",
            intent="分析 MCP 与传统函数调用方式的差异",
            query="MCP vs function calling agent tools",
        ),
        ResearchTask(
            id=3,
            title="MCP 的实际应用",
            intent="了解 MCP 在智能体项目中的应用场景",
            query="Model Context Protocol use cases",
        ),
    ]

    state = ResearchState(
        topic=topic,
        tasks=tasks,
    )

    print("=" * 70)
    print("Deep Research Agent 数据模型演示")
    print("=" * 70)

    print(f"研究主题：{state.topic}")
    print(f"研究状态：{state.status.value}")
    print(f"子任务数量：{len(state.tasks)}")

    for task in state.tasks:
        print()
        print(f"任务 {task.id}：{task.title}")
        print(f"研究目的：{task.intent}")
        print(f"搜索关键词：{task.query}")
        print(f"任务状态：{task.status.value}")

    print()
    print("=" * 70)
    print("JSON 序列化结果")
    print("=" * 70)

    print(
        state.model_dump_json(
            indent=2,
        )
    )


if __name__ == "__main__":
    main()