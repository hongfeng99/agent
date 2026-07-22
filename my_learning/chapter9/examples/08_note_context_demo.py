import sys
from pathlib import Path


CHAPTER9_DIR = (
    Path(__file__).resolve().parent.parent
)

sys.path.insert(
    0,
    str(CHAPTER9_DIR),
)


from context import (
    ContextBuilder,
    ContextConfig,
)
from integrations import NoteContextAdapter
from tools import NoteTool


def create_note_if_missing(
    note_tool: NoteTool,
    title: str,
    content: str,
    note_type: str,
    tags: list[str],
) -> None:
    """
    只在同名笔记不存在时创建，
    避免重复运行示例产生大量重复笔记。
    """

    existing_notes = note_tool.run({
        "action": "list",
        "limit": 100,
    })

    existing_titles = {
        note.get("title")
        for note in existing_notes
    }

    if title in existing_titles:
        return

    note_tool.run({
        "action": "create",
        "title": title,
        "content": content,
        "note_type": note_type,
        "tags": tags,
    })


def main() -> None:
    """
    测试 NoteTool 与 ContextBuilder 的集成。
    """

    workspace = (
        CHAPTER9_DIR
        / "data"
        / "note_context_demo"
    )

    note_tool = NoteTool(
        workspace=workspace
    )

    builder = ContextBuilder(
        config=ContextConfig(
            max_tokens=400,
            reserve_ratio=0.2,
            min_relevance=0.1,
            enable_compression=True,
        )
    )

    adapter = NoteContextAdapter(
        note_tool=note_tool,
        context_builder=builder,
    )

    # 1. 准备演示笔记。
    create_note_if_missing(
        note_tool=note_tool,
        title="Chapter 9 当前阻塞",
        content=(
            "目前还没有实现 TerminalTool，"
            "因此 Agent 还不能即时读取项目文件。"
        ),
        note_type="blocker",
        tags=[
            "chapter9",
            "terminal-tool",
        ],
    )

    create_note_if_missing(
        note_tool=note_tool,
        title="TerminalTool 下一步任务",
        content=(
            "下一步实现安全的 TerminalTool，"
            "需要限制工作目录、文件类型和输出长度。"
        ),
        note_type="action",
        tags=[
            "chapter9",
            "terminal-tool",
        ],
    )

    create_note_if_missing(
        note_tool=note_tool,
        title="ContextBuilder 阶段结论",
        content=(
            "ContextBuilder 的 GSSC 流水线"
            "和单元测试已经完成。"
        ),
        note_type="conclusion",
        tags=[
            "chapter9",
            "context-builder",
        ],
    )

    user_query = (
        "TerminalTool 接下来应该如何实现？"
    )

    # 2. 检索笔记。
    relevant_notes = (
        adapter.retrieve_relevant_notes(
            query="TerminalTool",
            limit=3,
        )
    )

    print("检索到的相关笔记：")

    for index, note in enumerate(
        relevant_notes,
        start=1,
    ):
        print("-" * 60)
        print(f"编号：{index}")
        print(f"标题：{note['title']}")
        print(f"类型：{note['type']}")
        print(f"正文：{note['content']}")

    # 3. 转换成 ContextPacket。
    note_packets = adapter.notes_to_packets(
        relevant_notes
    )

    print("\n转换后的 ContextPacket：")

    for index, packet in enumerate(
        note_packets,
        start=1,
    ):
        print("-" * 60)
        print(f"编号：{index}")
        print(
            f"相关性："
            f"{packet.relevance_score}"
        )
        print(
            f"token 数："
            f"{packet.token_count}"
        )
        print(
            f"元数据："
            f"{packet.metadata}"
        )

    # 4. 注入 ContextBuilder。
    final_context = builder.build(
        user_query=user_query,
        system_instructions=(
            "你是一位负责维护 Python Agent "
            "项目进度的长期助手。"
        ),
        custom_packets=note_packets,
    )

    print("\n" + "=" * 70)
    print("包含笔记的最终上下文")
    print("=" * 70)
    print(final_context)
    print("=" * 70)


if __name__ == "__main__":
    main()