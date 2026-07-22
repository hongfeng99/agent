import sys
from pathlib import Path


CHAPTER9_DIR = (
    Path(__file__).resolve().parent.parent
)

PROJECT_DIR = CHAPTER9_DIR.parent.parent

sys.path.insert(
    0,
    str(CHAPTER9_DIR),
)


from context import (
    ContextBuilder,
    ContextConfig,
)
from integrations import TerminalContextAdapter
from tools import TerminalTool


def main() -> None:
    """
    测试 TerminalTool 与 ContextBuilder 的集成。
    """

    terminal_tool = TerminalTool(
        workspace=PROJECT_DIR,
        max_output_chars=12_000,
        max_file_size=1_000_000,
    )

    context_builder = ContextBuilder(
        config=ContextConfig(
            max_tokens=1200,
            reserve_ratio=0.2,
            min_relevance=0.1,
            enable_compression=True,
            relevance_weight=0.7,
            recency_weight=0.3,
        )
    )

    adapter = TerminalContextAdapter(
        terminal_tool=terminal_tool,
        context_builder=context_builder,
    )

    # 1. 获取 Chapter 9 目录结构。
    structure_packet = (
        adapter.collect_structure(
            path="my_learning/chapter9",
            max_depth=2,
        )
    )

    # 2. 搜索 ContextBuilder 定义。
    search_packet = adapter.collect_search(
        query="class ContextBuilder",
        path="my_learning/chapter9",
        max_results=10,
    )

    # 3. 读取 ContextBuilder 部分源码。
    file_packet = adapter.collect_file(
        path=(
            "my_learning/chapter9/"
            "context/builder.py"
        ),
        start_line=1,
        end_line=100,
    )

    terminal_packets = [
        structure_packet,
        search_packet,
        file_packet,
    ]

    print("TerminalTool 生成的 ContextPacket：")

    for index, packet in enumerate(
        terminal_packets,
        start=1,
    ):
        print("-" * 70)
        print(f"编号：{index}")
        print(
            f"类型："
            f"{packet.metadata['type']}"
        )
        print(
            f"来源："
            f"{packet.metadata['source']}"
        )
        print(
            f"相关性："
            f"{packet.relevance_score}"
        )
        print(
            f"token 数："
            f"{packet.token_count}"
        )

    user_query = (
        "请根据当前代码说明 "
        "ContextBuilder 的主要职责和处理流程。"
    )

    final_context = adapter.build_context(
        user_query=user_query,
        terminal_packets=terminal_packets,
        system_instructions=(
            "你是一位负责分析 Python Agent "
            "项目源码的代码助手。"
        ),
    )

    print("\n" + "=" * 80)
    print("最终结构化上下文")
    print("=" * 80)
    print(final_context)
    print("=" * 80)

    print(
        "\n最终 token 数："
        f"{context_builder._count_tokens(final_context)}"
    )


if __name__ == "__main__":
    main()