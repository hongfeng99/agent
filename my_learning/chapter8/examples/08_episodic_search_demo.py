from datetime import datetime, timedelta

from memory import (
    EpisodicMemory,
    MemoryConfig,
    MemoryItem,
)


def print_results(
    title: str,
    memories: list[MemoryItem],
) -> None:
    """
    输出搜索结果。
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
            f"   重要性：{item.importance}\n"
            f"   事件类型："
            f"{item.metadata.get('event_type')}\n"
            f"   会话 ID："
            f"{item.metadata.get('session_id')}\n"
            f"   创建时间：{item.created_at}\n"
        )


def main() -> None:
    config = MemoryConfig(
        storage_path=(
            "data/episodic_search.json"
        ),
        default_search_limit=5,
        min_importance=0.0,
    )

    memory = EpisodicMemory(
        config=config,
        storage_path=(
            "data/episodic_search.json"
        ),
    )

    memory.clear()

    first_item = MemoryItem(
        content=(
            "用户完成了 Hello-Agents "
            "Chapter 7 的工具系统。"
        ),
        importance=0.9,
        metadata={
            "event_type": "learning_progress",
            "session_id": "session_001",
        },
    )

    second_item = MemoryItem(
        content=(
            "用户开始学习 Chapter 8 "
            "中的记忆与检索。"
        ),
        importance=1.0,
        metadata={
            "event_type": "learning_progress",
            "session_id": "session_001",
        },
    )

    third_item = MemoryItem(
        content=(
            "用户运行 WorkingMemory "
            "时遇到了导入错误。"
        ),
        importance=0.8,
        metadata={
            "event_type": "programming_error",
            "session_id": "session_002",
        },
    )

    fourth_item = MemoryItem(
        content="用户今天吃了一个苹果。",
        importance=0.7,
        metadata={
            "event_type": "daily_event",
            "session_id": "session_003",
        },
    )

    # 模拟一条较早的学习事件
    first_item.created_at = (
        datetime.now()
        - timedelta(days=20)
    )

    memory.add(first_item)
    memory.add(second_item)
    memory.add(third_item)
    memory.add(fourth_item)

    query = "我目前学习 Agent 到哪一步了"

    all_results = memory.search(
        query=query,
    )

    print_results(
        "不使用过滤条件：",
        all_results,
    )

    learning_results = memory.search(
        query=query,
        event_type="learning_progress",
    )

    print_results(
        "只搜索学习进度事件：",
        learning_results,
    )

    error_results = memory.search(
        query="运行程序时发生了什么错误",
        event_type="programming_error",
        session_id="session_002",
    )

    print_results(
        "搜索 session_002 中的程序错误：",
        error_results,
    )

    recent_results = memory.search(
        query="学习 Chapter",
        start_time=(
            datetime.now()
            - timedelta(days=7)
        ),
    )

    print_results(
        "只搜索最近 7 天的学习事件：",
        recent_results,
    )

    important_results = memory.search(
        query="用户",
        min_importance=0.85,
    )

    print_results(
        "只搜索重要性不低于 0.85 的事件：",
        important_results,
    )


if __name__ == "__main__":
    main()