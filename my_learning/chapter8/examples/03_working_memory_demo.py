from datetime import datetime, timedelta

from memory import MemoryConfig, MemoryItem, WorkingMemory


def print_memories(
    title: str,
    memories: list[MemoryItem],
) -> None:
    """
    按统一格式输出记忆列表。
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
        )


def main() -> None:
    config = MemoryConfig(
        working_memory_capacity=3,
        working_memory_ttl_minutes=30,
        default_search_limit=5,
        min_importance=0.0,
    )

    memory = WorkingMemory(config=config)

    first_item = MemoryItem(
        content="用户正在学习 Hello-Agents Chapter 8。",
        importance=0.9,
        metadata={
            "source": "conversation",
        },
    )

    second_item = MemoryItem(
        content="用户已经完成 Chapter 7 的工具系统。",
        importance=0.8,
    )

    third_item = MemoryItem(
        content="用户今天喝了一杯水。",
        importance=0.1,
    )

    first_id = memory.add(first_item)
    memory.add(second_item)
    memory.add(third_item)

    print_memories(
        "第一次添加后的全部工作记忆：",
        memory.get_all(),
    )

    print("当前记忆数量：", len(memory))

    search_results = memory.search("Chapter")

    print_memories(
        "搜索 Chapter 的结果：",
        search_results,
    )

    # 测试重复记忆
    duplicated_item = MemoryItem(
        content="用户正在学习 Hello-Agents Chapter 8。",
        importance=1.0,
        metadata={
            "status": "confirmed",
        },
    )

    duplicated_id = memory.add(duplicated_item)

    print("\n测试重复记忆：")
    print("原始记忆 ID：", first_id)
    print("重复添加后返回的 ID：", duplicated_id)
    print("当前记忆数量：", len(memory))

    print_memories(
        "重复添加后的全部记忆：",
        memory.get_all(),
    )

    # 添加第四条记忆，测试容量限制
    fourth_item = MemoryItem(
        content="用户偏好详细解释 Python 代码。",
        importance=0.95,
    )

    memory.add(fourth_item)

    print_memories(
        "添加第四条记忆后的结果：",
        memory.get_all(),
    )

    print(
        "容量上限为 3，低重要性的"
        "“用户今天喝了一杯水”应当被删除。"
    )

    # 手动创建一条已过期记忆
    expired_item = MemoryItem(
        content="这是一条已经过期的测试记忆。",
        importance=0.7,
    )

    expired_item.created_at = (
        datetime.now() - timedelta(minutes=60)
    )

    # 为了单独测试过期清理，直接放入内部列表
    memory.memories.append(expired_item)

    print("\n清理前记忆数量：", len(memory.memories))

    removed_count = memory.cleanup_expired()

    print("过期删除数量：", removed_count)
    print("清理后记忆数量：", len(memory.memories))

    # 测试删除
    removed = memory.remove(first_id)

    print("\n删除第一条记忆：")
    print("是否删除成功：", removed)

    print_memories(
        "删除后的全部记忆：",
        memory.get_all(),
    )


if __name__ == "__main__":
    main()