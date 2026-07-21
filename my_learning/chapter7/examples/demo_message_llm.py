from hello_agents.llm import HelloAgentsLLM
from hello_agents.message import Message


def main() -> None:
    """
    测试 Message 和 HelloAgentsLLM 配合使用。
    """

    llm = HelloAgentsLLM()

    system_message = Message(
        role="system",
        content="你是一个回答简洁的编程助手。",
    )

    user_message = Message(
        role="user",
        content="请用一句话解释什么是 Agent。",
    )

    messages = [
        system_message.to_dict(),
        user_message.to_dict(),
    ]

    result = llm.invoke(
        messages=messages,
        temperature=0,
    )

    assistant_message = Message(
        role="assistant",
        content=result,
    )

    print("发送给模型的消息：")
    print(messages)

    print("\n模型回答：")
    print(assistant_message.content)

    print("\n完整助手消息对象：")
    print(assistant_message)


if __name__ == "__main__":
    main()