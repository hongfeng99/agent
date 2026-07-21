from hello_agents import (
    TavilySearchTool,
    ToolRegistry,
)


def main() -> None:
    registry = ToolRegistry()

    registry.register(
        TavilySearchTool(
            default_max_results=3,
        )
    )

    print("当前工具：")
    print(
        registry.format_tools_description()
    )

    result = registry.execute(
        name="tavily_search",
        parameters={
            "query": (
                "Tavily Python SDK 官方安装命令"
            ),
            "max_results": 3,
        },
    )

    print("\n搜索结果：")
    print(result)


if __name__ == "__main__":
    main()