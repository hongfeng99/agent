import sys
from pathlib import Path


# 获取 chapter8 目录
CHAPTER8_DIR = Path(__file__).resolve().parents[1]

# 将 chapter8 加入 Python 模块搜索路径
if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER8_DIR))


from memory.base import MemoryItem
from memory.manager import MemoryManager
from memory.types.episodic import EpisodicMemory
from memory.types.semantic import SemanticMemory
from memory.types.working import WorkingMemory


def print_memory(item: MemoryItem) -> None:
    """
    打印一条记忆。
    """

    print(f"内容：{item.content}")
    print(f"ID：{item.id}")
    print(f"类型：{item.memory_type}")
    print(f"重要性：{item.importance}")
    print(f"创建时间：{item.created_at}")
    print(f"元数据：{item.metadata}")
    print("-" * 50)


def main() -> None:
    """
    测试 MemoryManager 的基本功能。
    """

    # 1. 创建三个底层记忆模块
    working_memory = WorkingMemory()

    episodic_memory = EpisodicMemory(
        storage_path="data/manager_episodic_memories.json",
    )

    semantic_memory = SemanticMemory(
        storage_path="data/manager_semantic_memories.json",
    )

    # 2. 创建统一的记忆管理器
    manager = MemoryManager(
        memories={
            "working": working_memory,
            "episodic": episodic_memory,
            "semantic": semantic_memory,
        }
    )

    # 3. 清空本次测试使用的数据
    # 注意：这里使用的是单独的 manager 测试文件，
    # 不会清空你之前的 episodic_memories.json。
    manager.clear()

    # 4. 添加工作记忆
    working_item = MemoryItem(
        content="今天需要完成 MemoryManager 的实现。",
        memory_type="working",
        importance=0.6,
        metadata={
            "category": "task",
            "chapter": 8,
        },
    )

    manager.add(working_item)

    # 5. 添加情景记忆
    episodic_item = MemoryItem(
        content="我已经完成了 SemanticMemory 的基础实现。",
        memory_type="episodic",
        importance=0.8,
        metadata={
            "category": "learning_event",
            "chapter": 8,
        },
    )

    manager.add(episodic_item)

    # 6. 添加语义记忆
    semantic_item_1 = MemoryItem(
        content="WorkingMemory 使用纯内存保存数据，程序结束后数据会消失。",
        memory_type="semantic",
        importance=0.9,
        metadata={
            "category": "knowledge",
            "topic": "WorkingMemory",
        },
    )

    semantic_item_2 = MemoryItem(
        content="TF-IDF 可以把文本转换成数值向量，用于计算文本相似度。",
        memory_type="semantic",
        importance=0.8,
        metadata={
            "category": "knowledge",
            "topic": "TF-IDF",
        },
    )

    manager.add(semantic_item_1)
    manager.add(semantic_item_2)

    # 7. 查看各类记忆的数量
    print("记忆数量统计：")

    stats = manager.stats()

    for memory_type, count in stats.items():
        print(f"{memory_type}: {count}")

    print("=" * 60)

    # 8. 搜索全部记忆
    query = "程序结束后哪种记忆的数据会消失？"

    print(f"查询内容：{query}")
    print()

    results = manager.search(
        query=query,
        limit=5,
    )

    print(f"共找到 {len(results)} 条结果：")
    print()

    for index, item in enumerate(results, start=1):
        print(f"第 {index} 条结果")
        print_memory(item)

    # 9. 只搜索语义记忆
    print("=" * 60)
    print("只搜索 semantic 记忆：")

    semantic_results = manager.search(
        query="文本如何转换成向量？",
        memory_types=["semantic"],
        limit=3,
    )

    for index, item in enumerate(
        semantic_results,
        start=1,
    ):
        print(f"第 {index} 条结果")
        print_memory(item)

    # 10. 获取全部记忆
    all_memories = manager.get_all()

    print("=" * 60)
    print(f"当前共有 {len(all_memories)} 条记忆。")


if __name__ == "__main__":
    main()