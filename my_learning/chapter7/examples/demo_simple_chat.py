from hello_agents import Config, HelloAgentsLLM, SimpleAgent


def main() -> None:
    """
    测试 SimpleAgent 的多轮对话和历史记录。
    """

    llm = HelloAgentsLLM()

    config = Config(
        temperature=0,
        max_tokens=500,
        max_history_length=10,
        debug=False,
    )

    agent = SimpleAgent(
        name="记忆测试助手",
        llm=llm,
        system_prompt="你是一个能够根据对话历史回答问题的助手。",
        config=config,
    )

    first_result = agent.run(
        "我正在学习 Python Agent 开发，我的学习项目叫 Hello-Agents。"
    )

    print("第一轮回答：")
    print(first_result)

    second_result = agent.run(
        "我刚才说我正在学习什么？项目叫什么？"
    )

    print("\n第二轮回答：")
    print(second_result)

    print("\nAgent 当前保存的历史消息：")

    for index, message in enumerate(
        agent.get_history(),
        start=1,
    ):
        print(
            f"{index}. "
            f"role={message.role}, "
            f"content={message.content}"
        )

    agent.clear_history()

    print("\n清空历史记录以后：")
    print(agent.get_history())


    third_result = agent.run(
        "我的学习项目叫什么？"
    )

    print("\n清空历史后的回答：")
    print(third_result)

if __name__ == "__main__":
    main()