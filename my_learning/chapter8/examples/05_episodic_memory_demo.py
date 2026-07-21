from memory import (
    EpisodicMemory,
    MemoryConfig,
    MemoryItem,
)


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

    for index, item in enumerate(
        memories,
        start=1,
    ):
        print(
            f"{index}. {item.content}\n"
            f"   ID：{item.id}\n"
            f"   类型：{item.memory_type}\n"
            f"   重要性：{item.importance}\n"
            f"   创建时间：{item.created_at}\n"
            f"   元数据：{item.metadata}\n"
        )


def main() -> None:
    config = MemoryConfig(
        storage_path="data/memories.json",
        default_search_limit=3,
        min_importance=0.0,
    )

    memory = EpisodicMemory(
        config=config,
        storage_path=(
            "data/episodic_memories.json"
        ),
    )

    # 演示时先清空旧测试数据
    memory.clear()

    first_item = MemoryItem(
        content=(
            "用户完成了 Hello-Agents "
            "Chapter 7 的学习。"
        ),
        importance=0.9,
        metadata={
            "event_type": "learning_progress",
            "source": "conversation",
        },
    )

    second_item = MemoryItem(
        content=(
            "用户开始学习 Hello-Agents "
            "Chapter 8。"
        ),
        importance=1.0,
        metadata={
            "event_type": "learning_progress",
        },
    )

    third_item = MemoryItem(
        content=(
            "用户运行 JSON 存储测试时"
            "成功生成了数据文件。"
        ),
        importance=0.7,
        metadata={
            "event_type": "programming_event",
        },
    )

    first_id = memory.add(first_item)
    second_id = memory.add(second_item)
    memory.add(third_item)

    print("第一条记忆 ID：", first_id)
    print("第二条记忆 ID：", second_id)
    print("当前记忆数量：", len(memory))

    print_memories(
        "全部情景记忆：",
        memory.get_all(),
    )

    results = memory.search(
        "Chapter",
    )

    print_memories(
        "搜索 Chapter 的结果：",
        results,
    )

    # 测试重要性过滤
    important_results = memory.search(
        query="用户",
        min_importance=0.8,
    )

    print_memories(
        "重要性不低于 0.8 的搜索结果：",
        important_results,
    )

    # 测试重复内容
    duplicated_item = MemoryItem(
        content=(
            "用户开始学习 Hello-Agents "
            "Chapter 8。"
        ),
        importance=0.8,
        metadata={
            "status": "confirmed",
        },
    )

    duplicated_id = memory.add(
        duplicated_item
    )

    print("\n重复记忆测试：")
    print("原始 ID：", second_id)
    print("重复添加返回 ID：", duplicated_id)
    print("当前记忆数量：", len(memory))

    print_memories(
        "重复添加后的记忆：",
        memory.get_all(),
    )

    # 模拟程序重新启动
    restarted_memory = EpisodicMemory(
        config=config,
        storage_path=(
            "data/episodic_memories.json"
        ),
    )

    print_memories(
        "重新创建 EpisodicMemory 后的记忆：",
        restarted_memory.get_all(),
    )

    # 测试更新
    found_item = restarted_memory.get(
        first_id
    )

    if found_item is not None:
        found_item.importance = 1.0
        found_item.metadata[
            "status"
        ] = "completed"

        updated = restarted_memory.update(
            found_item
        )

        print("\n是否更新成功：", updated)

    print_memories(
        "更新后的记忆：",
        restarted_memory.get_all(),
    )

    # 测试删除
    removed = restarted_memory.remove(
        third_item.id
    )

    print("\n是否删除第三条记忆：", removed)

    print_memories(
        "删除后的记忆：",
        restarted_memory.get_all(),
    )


if __name__ == "__main__":
    main()