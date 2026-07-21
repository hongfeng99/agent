from memory import JsonMemoryStorage, MemoryItem


def print_memories(
    title: str,
    memories: list[MemoryItem],
) -> None:
    """
    输出记忆列表。
    """

    print(f"\n{title}")

    if not memories:
        print("没有记忆。")
        return

    for index, item in enumerate(memories, start=1):
        print(
            f"{index}. {item.content}\n"
            f"   ID：{item.id}\n"
            f"   类型：{item.memory_type}\n"
            f"   重要性：{item.importance}\n"
            f"   创建时间：{item.created_at}\n"
            f"   元数据：{item.metadata}\n"
        )


def main() -> None:
    storage = JsonMemoryStorage(
        "data/test_memories.json"
    )

    # 每次演示前先清空旧数据，
    # 避免多次运行后产生重复测试数据。
    storage.clear()

    first_memory = MemoryItem(
        content="用户已经完成 Chapter 7。",
        memory_type="episodic",
        importance=0.9,
        metadata={
            "source": "learning_progress",
        },
    )

    second_memory = MemoryItem(
        content="用户正在学习 Chapter 8。",
        memory_type="semantic",
        importance=1.0,
        metadata={
            "source": "conversation",
        },
    )

    first_id = storage.add(first_memory)
    second_id = storage.add(second_memory)

    print("第一条记忆 ID：", first_id)
    print("第二条记忆 ID：", second_id)
    print("当前记忆数量：", storage.count())

    loaded_memories = storage.load()

    print_memories(
        "第一次读取 JSON 文件：",
        loaded_memories,
    )

    # 创建一个新的 storage 对象，
    # 模拟程序重新启动。
    restarted_storage = JsonMemoryStorage(
        "data/test_memories.json"
    )

    restarted_memories = restarted_storage.load()

    print_memories(
        "重新创建存储对象后的读取结果：",
        restarted_memories,
    )

    # 测试根据 ID 获取记忆
    found_memory = restarted_storage.get(first_id)

    print("\n根据 ID 查找第一条记忆：")

    if found_memory is not None:
        print(found_memory.content)
    else:
        print("没有找到。")

    # 测试更新
    if found_memory is not None:
        found_memory.importance = 1.0

        found_memory.metadata["status"] = "confirmed"

        updated = restarted_storage.update(
            found_memory
        )

        print("\n是否更新成功：", updated)

    print_memories(
        "更新后的记忆：",
        restarted_storage.load(),
    )

    # 测试删除
    removed = restarted_storage.remove(second_id)

    print("\n是否删除第二条记忆：", removed)
    print(
        "删除后的记忆数量：",
        restarted_storage.count(),
    )

    print_memories(
        "删除后的全部记忆：",
        restarted_storage.load(),
    )


if __name__ == "__main__":
    main()