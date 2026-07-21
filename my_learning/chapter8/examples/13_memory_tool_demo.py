import json
import sys
from pathlib import Path


CHAPTER8_DIR = Path(__file__).resolve().parents[1]

if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER8_DIR))


from memory.manager import MemoryManager
from memory.types.episodic import EpisodicMemory
from memory.types.working import WorkingMemory
from tools.memory_tool import MemoryTool


DATA_DIR = CHAPTER8_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

EPISODIC_STORAGE_PATH = (
    DATA_DIR / "memory_tool_episodic.json"
)


def create_memory_tool() -> MemoryTool:
    """
    创建 MemoryTool。
    """

    working_memory = WorkingMemory()

    episodic_memory = EpisodicMemory(
        storage_path=str(
            EPISODIC_STORAGE_PATH
        ),
    )

    manager = MemoryManager(
        memories={
            "working": working_memory,
            "episodic": episodic_memory,
        }
    )

    return MemoryTool(manager)


def run_tool(
    tool: MemoryTool,
    title: str,
    data: dict,
) -> dict:
    """
    调用 MemoryTool，并打印结果。
    """

    print("=" * 70)
    print(title)
    print("=" * 70)

    tool_input = json.dumps(
        data,
        ensure_ascii=False,
    )

    print("工具输入：")
    print(tool_input)
    print()

    result_text = tool.run(tool_input)

    print("工具输出：")
    print(result_text)
    print()

    return json.loads(result_text)


def main() -> None:
    """
    测试 MemoryTool 的主要功能。
    """

    memory_tool = create_memory_tool()

    # 清空上一次测试数据
    run_tool(
        tool=memory_tool,
        title="1. 清空测试数据",
        data={
            "action": "clear",
        },
    )

    # 添加第一条工作记忆
    add_result_1 = run_tool(
        tool=memory_tool,
        title="2. 添加普通工作记忆",
        data={
            "action": "add",
            "content": "接下来需要学习 MemoryTool。",
            "memory_type": "working",
            "importance": 0.6,
            "metadata": {
                "chapter": 8,
                "status": "进行中",
            },
        },
    )

    first_memory_id = (
        add_result_1["result"]["id"]
    )

    # 添加第二条高重要性工作记忆
    run_tool(
        tool=memory_tool,
        title="3. 添加高重要性工作记忆",
        data={
            "action": "add",
            "content": "我已经完成了 MemoryManager。",
            "memory_type": "working",
            "importance": 0.9,
            "metadata": {
                "chapter": 8,
                "status": "已完成",
            },
        },
    )

    # 搜索记忆
    run_tool(
        tool=memory_tool,
        title="4. 搜索 Chapter 8 学习记忆",
        data={
            "action": "search",
            "query": "Chapter 8 学习进度",
            "memory_types": ["working"],
            "limit": 5,
        },
    )

    # 更新第一条记忆
    run_tool(
        tool=memory_tool,
        title="5. 更新第一条记忆",
        data={
            "action": "update",
            "memory_id": first_memory_id,
            "content": (
                "我已经完成了 MemoryTool "
                "的基础实现。"
            ),
            "importance": 0.8,
            "metadata": {
                "status": "已完成",
            },
        },
    )

    # 查看统计
    run_tool(
        tool=memory_tool,
        title="6. 查看整合前统计",
        data={
            "action": "stats",
        },
    )

    # 将高重要性工作记忆整合到情景记忆
    run_tool(
        tool=memory_tool,
        title="7. 整合高重要性记忆",
        data={
            "action": "consolidate",
            "source_type": "working",
            "target_type": "episodic",
            "min_importance": 0.7,
            "remove_from_source": True,
        },
    )

    # 查看整合后的统计
    run_tool(
        tool=memory_tool,
        title="8. 查看整合后统计",
        data={
            "action": "stats",
        },
    )

    # 搜索情景记忆
    run_tool(
        tool=memory_tool,
        title="9. 搜索整合后的情景记忆",
        data={
            "action": "search",
            "query": "已经完成哪些模块",
            "memory_types": ["episodic"],
            "limit": 5,
        },
    )

    # 测试错误输入
    run_tool(
        tool=memory_tool,
        title="10. 测试不支持的 action",
        data={
            "action": "unknown_action",
        },
    )


if __name__ == "__main__":
    main()