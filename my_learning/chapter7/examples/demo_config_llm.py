from hello_agents import Config, HelloAgentsLLM, Message


def main() -> None:
    """
    测试 Config、Message 和 HelloAgentsLLM 配合使用。
    """

    config = Config(
        temperature=0,
        max_tokens=300,
        debug=True,
    )

    llm = HelloAgentsLLM()

    user_message = Message(
        role="user",
        content="请用一句话解释 Agent 框架的作用。",
    )

    messages = [
        user_message.to_dict(),
    ]

    if config.debug:
        print("发送给模型的消息：")
        print(messages)

    result = llm.invoke(
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )

    print("\n模型回答：")
    print(result)


if __name__ == "__main__":
    main()