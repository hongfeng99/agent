from hello_agents import Config, HelloAgentsLLM, SimpleAgent


def main() -> None:
    """
    测试 SimpleAgent 的单轮对话。
    """

    llm = HelloAgentsLLM()

    config = Config(
        temperature=0,
        max_tokens=500,
        max_history_length=20,
        debug=True,
    )

    agent = SimpleAgent(
        name="Python学习助手",
        llm=llm,
        system_prompt=(
            "你是一位耐心的 Python 编程老师。"
            "请使用简单、准确的语言回答初学者的问题。"
        ),
        config=config,
    )

    result = agent.run(
        "请用一句话解释什么是 Python 类。"
    )

    print("\n最终回答：")
    print(result)


if __name__ == "__main__":
    main()