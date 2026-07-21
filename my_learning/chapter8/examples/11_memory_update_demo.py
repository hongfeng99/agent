import sys
from pathlib import Path


CHAPTER8_DIR = Path(__file__).resolve().parents[1]

if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER8_DIR))


from memory.base import MemoryItem
from memory.manager import MemoryManager
from memory.types.episodic import EpisodicMemory


STORAGE_PATH = "data/manager_update_demo.json"


def print_item(
    title: str,
    item: MemoryItem | None,
) -> None:
    """
    打印记忆内容。
    """

    print(title)

    if item is None:
        print("没有找到记忆。")
        print("-" * 60)
        return

    print(f"ID：{item.id}")
    print(f"内容：{item.content}")
    print(f"类型：{item.memory_type}")
    print(f"重要性：{item.importance}")
    print(f"元数据：{item.metadata}")
    print("-" * 60)


def create_manager() -> MemoryManager:
    """
    创建只包含情景记忆的管理器。
    """

    episodic_memory = EpisodicMemory(
        storage_path=STORAGE_PATH,
    )

    return MemoryManager(
        memories={
            "episodic": episodic_memory,
        }
    )


def main() -> None:
    """
    测试记忆查找和更新。
    """

    # 1. 创建管理器
    manager = create_manager()

    # 2. 清空上一次测试数据
    manager.clear()

    # 3. 创建并添加记忆
    original_item = MemoryItem(
        content="我正在实现 MemoryManager。",
        memory_type="episodic",
        importance=0.6,
        metadata={
            "chapter": 8,
            "status": "进行中",
        },
    )

    manager.add(original_item)

    # 4. 根据 ID 查找原始记忆
    found_item = manager.get(original_item.id)

    print_item(
        "更新前：",
        found_item,
    )

    # 5. 更新记忆
    updated_item = manager.update(
        memory_id=original_item.id,
        content="我已经完成了 MemoryManager 的基础实现。",
        importance=0.9,
        metadata={
            "status": "已完成",
            "next_task": "memory lifecycle",
        },
    )

    print_item(
        "更新后：",
        updated_item,
    )

    # 6. 模拟程序重新启动
    reloaded_manager = create_manager()

    reloaded_item = reloaded_manager.get(
        original_item.id,
    )

    print_item(
        "重新创建管理器后读取到的记忆：",
        reloaded_item,
    )


if __name__ == "__main__":
    main()