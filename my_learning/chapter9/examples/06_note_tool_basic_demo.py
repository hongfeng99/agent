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
    测试 NoteTool 的 create、read 和 list。
    """

    notes_workspace = (
        CHAPTER9_DIR / "data" / "notes"
    )

    note_tool = NoteTool(
        workspace=notes_workspace
    )

    # 1. 创建笔记。
    note_id = note_tool.run({
        "action": "create",
        "title": "Chapter 9 ContextBuilder 进度",
        "content": """
## 已完成

- ContextPacket
- ContextConfig
- Gather
- Select
- Structure
- Compress
- ContextBuilder 单元测试

## 下一步

实现 NoteTool。
""",
        "note_type": "task_state",
        "tags": [
            "chapter9",
            "context-builder",
        ],
    })

    print("创建成功：")
    print(note_id)

    # 2. 读取刚创建的笔记。
    note = note_tool.run({
        "action": "read",
        "note_id": note_id,
    })

    print("\n读取结果：")
    print("元数据：")
    print(note["metadata"])

    print("\n正文：")
    print(note["content"])

    # 3. 列出所有笔记。
    all_notes = note_tool.run({
        "action": "list",
        "limit": 20,
    })

    print("\n全部笔记：")

    for index, metadata in enumerate(
        all_notes,
        start=1,
    ):
        print("-" * 60)
        print(f"编号：{index}")
        print(f"ID：{metadata['id']}")
        print(f"标题：{metadata['title']}")
        print(f"类型：{metadata['type']}")
        print(f"标签：{metadata['tags']}")
        print(
            f"更新时间："
            f"{metadata['updated_at']}"
        )

    # 4. 只列出 task_state 类型。
    task_notes = note_tool.run({
        "action": "list",
        "note_type": "task_state",
        "tags": ["chapter9"],
    })

    print(
        "\nChapter 9 的 task_state "
        f"笔记数量：{len(task_notes)}"
    )


if __name__ == "__main__":
    main()