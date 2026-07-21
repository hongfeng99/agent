from memory import (
    MemoryConfig,
    MemoryItem,
    SemanticMemory,
)


def print_memories(
    title: str,
    memories: list[MemoryItem],
) -> None:
    """
    输出语义记忆列表。
    """

    print(f"\n{title}")

    if not memories:
        print("没有找到相关记忆。")
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
            f"   分类："
            f"{item.metadata.get('category')}\n"
            f"   主题："
            f"{item.metadata.get('subject')}\n"
            f"   来源："
            f"{item.metadata.get('source')}\n"
        )


def main() -> None:
    config = MemoryConfig(
        storage_path=(
            "data/semantic_memories.json"
        ),
        default_search_limit=5,
        min_importance=0.0,
    )

    memory = SemanticMemory(
        config=config,
        storage_path=(
            "data/semantic_memories.json"
        ),
    )

    # 演示时先清空旧数据
    memory.clear()

    first_item = MemoryItem(
        content=(
            "用户主要使用 Python "
            "学习 Agent 开发。"
        ),
        importance=0.9,
        metadata={
            "category": "user_profile",
            "subject": "Python",
            "source": "conversation",
        },
    )

    second_item = MemoryItem(
        content=(
            "用户偏好逐行解释 "
            "Python 代码。"
        ),
        importance=1.0,
        metadata={
            "category": "user_preference",
            "subject": "Python",
            "source": "conversation",
        },
    )

    third_item = MemoryItem(
        content=(
            "Hello-Agents Chapter 8 "
            "主要介绍记忆与检索系统。"
        ),
        importance=0.9,
        metadata={
            "category": "knowledge",
            "subject": "Chapter 8",
            "source": "document",
        },
    )

    fourth_item = MemoryItem(
        content=(
            "WorkingMemory 使用纯内存，"
            "程序结束后数据会消失。"
        ),
        importance=0.8,
        metadata={
            "category": "knowledge",
            "subject": "WorkingMemory",
            "source": "document",
        },
    )

    fifth_item = MemoryItem(
        content="苹果是一种常见水果。",
        importance=0.7,
        metadata={
            "category": "knowledge",
            "subject": "fruit",
            "source": "manual",
        },
    )

    first_id = memory.add(first_item)
    memory.add(second_item)
    memory.add(third_item)
    memory.add(fourth_item)
    memory.add(fifth_item)

    print("第一条语义记忆 ID：", first_id)
    print("当前语义记忆数量：", len(memory))

    print_memories(
        "全部语义记忆：",
        memory.get_all(),
    )

    learning_results = memory.search(
        query="用户如何学习 Python Agent",
    )

    print_memories(
        "搜索用户的 Agent 学习方式：",
        learning_results,
    )

    preference_results = memory.search(
        query="用户喜欢怎样讲解代码",
        category="user_preference",
    )

    print_memories(
        "只搜索用户偏好：",
        preference_results,
    )

    chapter_results = memory.search(
        query="Chapter 8 学习什么内容",
        subject="Chapter 8",
        source="document",
    )

    print_memories(
        "搜索 Chapter 8 文档知识：",
        chapter_results,
    )

    # 测试重复记忆
    duplicated_item = MemoryItem(
        content=(
            "用户偏好逐行解释 "
            "Python 代码。"
        ),
        importance=0.8,
        metadata={
            "confirmed": True,
        },
    )

    original_count = len(memory)

    duplicated_id = memory.add(
        duplicated_item
    )

    print("\n重复记忆测试：")
    print("重复添加返回的 ID：", duplicated_id)
    print("添加前数量：", original_count)
    print("添加后数量：", len(memory))

    print_memories(
        "重复内容合并后的语义记忆：",
        memory.get_all(),
    )

    # 模拟程序重新启动
    restarted_memory = SemanticMemory(
        config=config,
        storage_path=(
            "data/semantic_memories.json"
        ),
    )

    print_memories(
        "重新创建 SemanticMemory 后：",
        restarted_memory.get_all(),
    )

    # 测试更新
    found_item = restarted_memory.get(
        first_id
    )

    if found_item is not None:
        found_item.importance = 1.0

        found_item.metadata[
            "confirmed"
        ] = True

        updated = restarted_memory.update(
            found_item
        )

        print("\n是否更新成功：", updated)

    print_memories(
        "更新后的语义记忆：",
        restarted_memory.get_all(),
    )


if __name__ == "__main__":
    main()