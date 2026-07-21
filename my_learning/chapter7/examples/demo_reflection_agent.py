from hello_agents import (
    Config,
    HelloAgentsLLM,
    ReflectionAgent,
)


def main() -> None:
    llm = HelloAgentsLLM()

    config = Config(
        temperature=0.2,
        max_tokens=1000,
        max_history_length=20,
        debug=True,
    )

    agent = ReflectionAgent(
        name="反思型学习助手",
        llm=llm,
        system_prompt=(
            "你是一位耐心、准确的 Python 和 Agent 开发老师。"
            "回答对象是刚开始学习 Python 的初学者。"
        ),
        config=config,
    )

    question = (
        "请解释 Python 中继承和组合的区别，"
        "并结合 Agent 框架各举一个例子。"
    )

    result = agent.run(question)

    print("\n====================")
    print("最终回答：")
    print(result)

    print("\n====================")
    print("初始答案：")
    print(agent.last_initial_answer)

    print("\n====================")
    print("反思意见：")
    print(agent.last_reflection)


    second_result = agent.run(
        "请再用更简单的语言总结刚才的区别。"
    )

    print("\n第二轮回答：")
    print(second_result)

if __name__ == "__main__":
    main()