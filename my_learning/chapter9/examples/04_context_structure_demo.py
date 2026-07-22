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
    测试 Gather、Select、Structure 三个阶段。
    """

    builder = ContextBuilder(
        config=ContextConfig(
            max_tokens=3000,
            min_relevance=0.1,
            relevance_weight=0.7,
            recency_weight=0.3,
        )
    )

    user_query = (
        "如何实现 Chapter 9 的 Structure 阶段？"
    )

    conversation_history = [
        {
            "role": "user",
            "content": (
                "Gather 阶段已经完成。"
            ),
            "timestamp": (
                datetime.now()
                - timedelta(hours=2)
            ),
        },
        {
            "role": "assistant",
            "content": (
                "接下来实现 Select 阶段。"
            ),
            "timestamp": (
                datetime.now()
                - timedelta(hours=1)
            ),
        },
        {
            "role": "user",
            "content": (
                "Select 阶段已经运行成功。"
            ),
            "timestamp": (
                datetime.now()
                - timedelta(minutes=10)
            ),
        },
    ]

    custom_packets = [
        ContextPacket(
            content=(
                "Structure 阶段负责把信息"
                "组织成固定的上下文分区。"
            ),
            timestamp=datetime.now(),
            token_count=22,
            relevance_score=0.9,
            metadata={
                "type": "knowledge",
                "source": "chapter9_document",
            },
        ),
        ContextPacket(
            content=(
                "上下文分区能够提高"
                "可读性和可调试性。"
            ),
            timestamp=datetime.now(),
            token_count=18,
            relevance_score=0.8,
            metadata={
                "type": "rag_result",
                "source": "knowledge_base",
            },
        ),
        ContextPacket(
            content=(
                "用户已经完成 Gather 和 Select。"
            ),
            timestamp=datetime.now(),
            token_count=15,
            relevance_score=0.9,
            metadata={
                "type": "memory",
                "source": "chapter8",
            },
        ),
    ]

    # 第一步：Gather。
    packets = builder._gather(
        user_query=user_query,
        conversation_history=conversation_history,
        system_instructions=(
            "你是一位耐心的 Python Agent 学习助手。"
        ),
        custom_packets=custom_packets,
    )

    # 第二步：Select。
    selected_packets = builder._select(
        packets=packets,
        user_query=user_query,
        available_tokens=150,
    )

    # 第三步：Structure。
    structured_context = builder._structure(
        selected_packets=selected_packets,
        user_query=user_query,
    )

    print("\n" + "=" * 70)
    print("最终结构化上下文")
    print("=" * 70)
    print(structured_context)
    print("=" * 70)


if __name__ == "__main__":
    main()