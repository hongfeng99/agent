from hello_agents import (
    CalculatorTool,
    Config,
    HelloAgentsLLM,
    ReActAgent,
    TavilySearchTool,
    ToolRegistry,
)


def main() -> None:
    llm = HelloAgentsLLM()

    config = Config(
        temperature=0,
        max_tokens=1000,
        max_history_length=20,
        max_steps=6,
        debug=True,
    )

    registry = ToolRegistry()

    registry.register(
        CalculatorTool()
    )

    registry.register(
        TavilySearchTool(
            default_max_results=3,
        )
    )

    print("可用工具：")
    print(
        registry.format_tools_description()
    )

    agent = ReActAgent(
        name="多工具ReAct助手",
        llm=llm,
        tool_registry=registry,
        system_prompt=(
            "你是一个严格遵守 ReAct 格式的助手。"
            "必须根据任务选择正确工具，"
            "不得伪造搜索结果或计算结果。"
        ),
        config=config,
    )

    question = (
        "请严格按照下面的顺序完成任务：\n"
        "1. 使用 tavily_search 搜索"
        "“2026年日本法定节假日数量”；\n"
        "2. 根据搜索结果确定节假日数量；\n"
        "3. 使用 calculator 将这个数量乘以2；\n"
        "4. 给出最终计算结果，并列出搜索来源。"
    )

    result = agent.run(question)

    print("\n====================")
    print("最终回答：")
    print(result)

    print("\n完整 ReAct 轨迹：")

    for item in agent.current_trace:
        print(item)


if __name__ == "__main__":
    main()