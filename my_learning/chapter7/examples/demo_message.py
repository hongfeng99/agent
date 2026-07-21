from hello_agents.message import Message


def main() -> None:
    """
    测试 Message 消息对象。
    """

    user_message = Message(
        role="user",
        content="你好，我正在学习 Chapter 7。",
    )

    assistant_message = Message(
        role="assistant",
        content="你好，欢迎学习 Agent 框架。",
        metadata={
            "agent_name": "SimpleAgent",
        },
    )

    print("用户消息对象：")
    print(user_message)

    print("\n用户消息的角色：")
    print(user_message.role)

    print("\n用户消息内容：")
    print(user_message.content)

    print("\n用户消息时间：")
    print(user_message.timestamp)

    print("\n用户消息字典：")
    print(user_message.to_dict())

    print("\n助手消息对象：")
    print(assistant_message)

    print("\n助手消息附加信息：")
    print(assistant_message.metadata)


if __name__ == "__main__":
    main()