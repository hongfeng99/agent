from memory.base import MemoryItem


def main() -> None:
    """
    测试 MemoryItem 是否能够正常创建。
    """

    memory = MemoryItem(
        content="用户正在学习 Hello-Agents Chapter 8。",
        memory_type="semantic",
        importance=0.9,
        metadata={
            "user_id": "user001",
            "source": "conversation",
        },
    )

    print("MemoryItem 对象：")
    print(memory)

    print("\n转换后的字典：")
    print(memory.to_dict())

    print("\n部分字段：")
    print("记忆 ID：", memory.id)
    print("记忆内容：", memory.content)
    print("记忆类型：", memory.memory_type)
    print("重要程度：", memory.importance)
    print("创建时间：", memory.created_at)


    print("\n测试非法 importance：")

    try:
        invalid_memory = MemoryItem(
            content="这是一条非法记忆。",
            importance=1.5,
        )
        print(invalid_memory)
    except ValueError as error:
        print("捕获到错误：", error)

    print("\n测试空内容：")

    try:
        empty_memory = MemoryItem(
            content="   ",
        )
        print(empty_memory)
    except ValueError as error:
        print("捕获到错误：", error)



if __name__ == "__main__":
    main()