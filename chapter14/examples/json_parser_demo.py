from chapter14.backend.utils.json_parser import (
    parse_research_tasks,
)


def main() -> None:
    """
    演示如何解析大模型返回的研究计划。
    """

    model_response = """
下面是针对该主题制定的研究计划：

```json
[
    {
        "title": "MCP 的基本概念",
        "intent": "了解 MCP 的设计目标和核心架构",
        "query": "Model Context Protocol architecture overview"
    },
    {
        "title": "MCP 与函数调用的区别",
        "intent": "分析 MCP 与传统函数调用的差异",
        "query": "MCP vs function calling"
    },
    {
        "title": "MCP 的实际应用",
        "intent": "了解 MCP 在智能体系统中的应用",
        "query": "Model Context Protocol agent use cases"
    }
]
```

以上是完整的研究计划。
"""

    tasks = parse_research_tasks(model_response)

    print("=" * 70)
    print("研究计划解析结果")
    print("=" * 70)

    for task in tasks:
        print()
        print(f"任务编号：{task.id}")
        print(f"任务标题：{task.title}")
        print(f"研究目的：{task.intent}")
        print(f"搜索关键词：{task.query}")
        print(f"任务状态：{task.status.value}")


if __name__ == "__main__":
    main()