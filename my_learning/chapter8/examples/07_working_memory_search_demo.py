from datetime import datetime, timedelta

from memory import (
    MemoryConfig,
    MemoryItem,
    WorkingMemory,
)


def main() -> None:
    """
    测试 WorkingMemory 的混合检索效果。
    """

    config = MemoryConfig(
        working_memory_capacity=10,
        working_memory_ttl_minutes=120,
        default_search_limit=5,
        min_importance=0.0,
    )

    memory = WorkingMemory(config=config)

    first_item = MemoryItem(
        content=(
            "用户正在学习 Hello-Agents "
            "Chapter 8 的记忆与检索功能。"
        ),
        importance=0.9,
    )

    second_item = MemoryItem(
        content=(
            "用户已经完成 Chapter 7 "
            "中的工具注册系统。"
        ),
        importance=0.8,
    )

    third_item = MemoryItem(
        content="用户正在学习 Python 智能体开发。",
        importance=0.7,
    )

    fourth_item = MemoryItem(
        content="用户今天吃了一个苹果。",
        importance=1.0,
    )

    # 把第三条记忆设置成较早的时间，
    # 用于观察时间衰减。
    third_item.created_at = (
        datetime.now()
        - timedelta(minutes=90)
    )

    memory.add(first_item)
    memory.add(second_item)
    memory.add(third_item)
    memory.add(fourth_item)

    query = "我正在学习 Agent 的记忆功能"

    results = memory.search(
        query=query,
        limit=4,
    )

    print("查询：")
    print(query)

    print("\n搜索结果：")

    if not results:
        print("没有找到相关记忆。")
        return

    for index, item in enumerate(
        results,
        start=1,
    ):
        age = datetime.now() - item.created_at

        print(
            f"{index}. {item.content}\n"
            f"   重要性：{item.importance}\n"
            f"   大约创建于："
            f"{age.total_seconds() / 60:.1f} 分钟前\n"
        )


if __name__ == "__main__":
    main()