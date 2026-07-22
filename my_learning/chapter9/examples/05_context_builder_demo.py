import sys
from datetime import datetime, timedelta
from pathlib import Path


CHAPTER9_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CHAPTER9_DIR))


from context import (
    ContextBuilder,
    ContextConfig,
    ContextPacket,
)


def main() -> None:
    """
    测试完整的 GSSC 流水线。
    """

    # 故意设置较小的 max_tokens，
    # 方便观察压缩效果。
    builder = ContextBuilder(
        config=ContextConfig(
            max_tokens=80,
            reserve_ratio=0.2,
            min_relevance=0.1,
            enable_compression=True,
            relevance_weight=0.7,
            recency_weight=0.3,
        )
    )

    user_query = (
        "Chapter 9 的 Compress 阶段有什么作用？"
    )

    conversation_history = [
        {
            "role": "user",
            "content": (
                "Gather、Select 和 Structure "
                "都已经运行成功。"
            ),
            "timestamp": (
                datetime.now()
                - timedelta(minutes=20)
            ),
        },
        {
            "role": "assistant",
            "content": (
                "接下来需要实现 Compress 阶段。"
            ),
            "timestamp": (
                datetime.now()
                - timedelta(minutes=10)
            ),
        },
    ]

    knowledge_content = (
        "压缩阶段会在上下文超过最大 token 限制时，"
        "按照结构化分区尽量保留完整内容；"
        "当某个分区无法完整放入剩余预算时，"
        "会对该分区执行截断处理。"
    )

    custom_packets = [
        ContextPacket(
            content=knowledge_content,
            timestamp=datetime.now(),
            token_count=builder._count_tokens(
                knowledge_content
            ),
            relevance_score=0.95,
            metadata={
                "type": "knowledge",
                "source": "chapter9_document",
            },
        ),
    ]

    final_context = builder.build(
        user_query=user_query,
        conversation_history=conversation_history,
        system_instructions=(
            "你是一位耐心的 Python Agent 学习助手。"
        ),
        custom_packets=custom_packets,
    )

    print("\n" + "=" * 70)
    print("最终上下文")
    print("=" * 70)
    print(final_context)
    print("=" * 70)

    final_tokens = builder._count_tokens(
        final_context
    )

    print(
        f"\n最终 token 数：{final_tokens}"
    )

    print(
        f"最大 token 限制："
        f"{builder.config.max_tokens}"
    )


if __name__ == "__main__":
    main()