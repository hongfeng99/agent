import sys
from pathlib import Path


CHAPTER8_DIR = Path(__file__).resolve().parents[1]

if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER8_DIR))


from memory.base import MemoryItem
from memory.manager import MemoryManager
from memory.types.episodic import EpisodicMemory
from memory.types.working import WorkingMemory


STORAGE_PATH = "data/lifecycle_episodic_memories.json"


def create_manager() -> MemoryManager:
    """
    创建包含工作记忆和情景记忆的管理器。
    """

    working_memory = WorkingMemory()

    episodic_memory = EpisodicMemory(
        storage_path=STORAGE_PATH,
    )

    return MemoryManager(
        memories={
            "working": working_memory,
            "episodic": episodic_memory,
        }
    )


def print_stats(
    manager: MemoryManager,
    title: str,
) -> None:
    """
    打印各类记忆数量。
    """

    print(title)

    stats = manager.stats()

    for memory_type, count in stats.items():
        print(f"{memory_type}: {count}")

    print("-" * 60)


def print_items(
    title: str,
    items: list[MemoryItem],
) -> None:
    """
    打印多条记忆。
    """

    print(title)

    if not items:
        print("没有记忆。")
        print("-" * 60)
        return

    for index, item in enumerate(items, start=1):
        print(f"{index}. {item.content}")
        print(f"   ID：{item.id}")
        print(f"   类型：{item.memory_type}")
        print(f"   重要性：{item.importance}")
        print(f"   元数据：{item.metadata}")

    print("-" * 60)


def main() -> None:
    """
    测试记忆遗忘和记忆整合。
    """

    manager = create_manager()

    # 清空上一次测试数据
    manager.clear()

    # 1. 添加低重要性工作记忆
    manager.add(
        MemoryItem(
            content="今天需要整理桌面。",
            memory_type="working",
            importance=0.2,
            metadata={
                "category": "temporary_task",
            },
        )
    )

    # 2. 添加中等重要性工作记忆
    manager.add(
        MemoryItem(
            content="接下来需要学习 MemoryTool。",
            memory_type="working",
            importance=0.6,
            metadata={
                "category": "learning_task",
                "chapter": 8,
            },
        )
    )

    # 3. 添加高重要性工作记忆
    manager.add(
        MemoryItem(
            content="我已经完成了 MemoryManager。",
            memory_type="working",
            importance=0.9,
            metadata={
                "category": "learning_progress",
                "chapter": 8,
            },
        )
    )

    # 4. 再添加一条高重要性工作记忆
    manager.add(
        MemoryItem(
            content="我已经实现了 SemanticMemory。",
            memory_type="working",
            importance=0.8,
            metadata={
                "category": "learning_progress",
                "chapter": 8,
            },
        )
    )

    print_stats(
        manager,
        "初始记忆数量：",
    )

    print_items(
        "初始工作记忆：",
        manager.get_all("working"),
    )

    # 5. 遗忘 importance 小于 0.4 的记忆
    forgotten_items = manager.forget(
        threshold=0.4,
        memory_types=["working"],
    )

    print_items(
        "被遗忘的记忆：",
        forgotten_items,
    )

    print_stats(
        manager,
        "遗忘后的记忆数量：",
    )

    # 6. 将重要性大于等于 0.7 的工作记忆
    # 整合到情景记忆
    consolidated_items = manager.consolidate(
        source_type="working",
        target_type="episodic",
        min_importance=0.7,
        remove_from_source=True,
    )

    print_items(
        "被整合到情景记忆中的内容：",
        consolidated_items,
    )

    print_stats(
        manager,
        "整合后的记忆数量：",
    )

    print_items(
        "整合后剩余的工作记忆：",
        manager.get_all("working"),
    )

    print_items(
        "整合后的情景记忆：",
        manager.get_all("episodic"),
    )

    # 7. 模拟程序重新启动
    print("=" * 60)
    print("模拟重新启动程序")
    print("=" * 60)

    reloaded_manager = create_manager()

    print_stats(
        reloaded_manager,
        "重新启动后的记忆数量：",
    )

    print_items(
        "重新启动后仍然存在的情景记忆：",
        reloaded_manager.get_all("episodic"),
    )


if __name__ == "__main__":
    main()