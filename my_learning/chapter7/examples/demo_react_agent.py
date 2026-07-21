from hello_agents import (
    CalculatorTool,
    Config,
    HelloAgentsLLM,
    ReActAgent,
    ToolRegistry,
)


def main() -> None:
    llm = HelloAgentsLLM()

    config = Config(
        temperature=0,
        max_tokens=800,
        max_history_length=20,
        max_steps=5,
        debug=True,
    )

    registry = ToolRegistry()

    registry.register(
        CalculatorTool()
    )

    agent = ReActAgent(
        name="数学ReAct助手",
        llm=llm,
        tool_registry=registry,
        system_prompt=(
            "你是一个严格遵守 ReAct 格式的助手。"
            "需要计算时必须使用 calculator 工具。"
        ),
        config=config,
    )

    question = (
        "请使用 calculator 工具计算 "
        "15 * 8 + 32，并说明最终结果。"
    )

    result = agent.run(question)

    print("\n====================")
    print("最终回答：")
    print(result)

    print("\n完整执行轨迹：")

    for item in agent.current_trace:
        print(item)

    print("\nAgent 对话历史：")

    for message in agent.get_history():
        print(
            f"role={message.role}, "
            f"content={message.content}"
        )


if __name__ == "__main__":
    main()