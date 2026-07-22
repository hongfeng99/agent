import json
import sys
from pathlib import Path


CHAPTER9_DIR = (
    Path(__file__).resolve().parent.parent
)

sys.path.insert(
    0,
    str(CHAPTER9_DIR),
)


from tools import NoteTool


def main() -> None:
    """
    测试 NoteTool 的七种完整操作。
    """

    workspace = (
        CHAPTER9_DIR
        / "data"
        / "note_tool_full_demo"
    )

    note_tool = NoteTool(
        workspace=workspace
    )

    # 1. create
    note_id = note_tool.run({
        "action": "create",
        "title": "Chapter 9 下一步任务",
        "content": """
## 当前进度

ContextBuilder 和 NoteTool 基础操作已经完成。

## 下一步

实现 TerminalTool。
""",
        "note_type": "action",
        "tags": [
            "chapter9",
            "note-tool",
        ],
    })

    print("1. 创建结果：")
    print(note_id)

    # 2. read
    note = note_tool.run({
        "action": "read",
        "note_id": note_id,
    })

    print("\n2. 读取结果：")
    print(note["metadata"])
    print(note["content"])

    # 3. update
    update_result = note_tool.run({
        "action": "update",
        "note_id": note_id,
        "title": "Chapter 9 TerminalTool 任务",
        "content": """
## 已完成

- ContextBuilder
- NoteTool

## 下一步

实现安全的 TerminalTool，并限制工作目录。
""",
        "note_type": "action",
        "tags": [
            "chapter9",
            "terminal-tool",
            "todo",
        ],
    })

    print("\n3. 更新结果：")
    print(update_result)

    # 4. search
    search_results = note_tool.run({
        "action": "search",
        "query": "TerminalTool",
        "limit": 10,
    })

    print("\n4. 搜索结果：")

    for result in search_results:
        print("-" * 60)
        print(f"ID：{result['note_id']}")
        print(f"标题：{result['title']}")
        print(f"类型：{result['type']}")
        print(f"标签：{result['tags']}")
        print(f"正文：\n{result['content']}")

    # 5. list
    action_notes = note_tool.run({
        "action": "list",
        "note_type": "action",
        "tags": ["chapter9"],
        "limit": 20,
    })

    print("\n5. action 类型笔记数量：")
    print(len(action_notes))

    # 6. summary
    summary = note_tool.run({
        "action": "summary",
    })

    print("\n6. 笔记摘要：")
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
    )

    # 7. delete
    delete_result = note_tool.run({
        "action": "delete",
        "note_id": note_id,
    })

    print("\n7. 删除结果：")
    print(delete_result)

    remaining_notes = note_tool.run({
        "action": "list",
    })

    print("\n删除后剩余笔记数量：")
    print(len(remaining_notes))


if __name__ == "__main__":
    main()