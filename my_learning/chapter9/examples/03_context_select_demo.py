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
    测试 Select 阶段。
    """

    builder = ContextBuilder(
        config=ContextConfig(
            max_tokens=3000,
            min_relevance=0.1,
            relevance_weight=0.7,
            recency_weight=0.3,
        )
    )

    conversation_history = [
        {
            "role": "user",
            "content": "ContextPacket 已经完成。",
            "timestamp": (
                datetime.now()
                - timedelta(hours=4)
            ),
        },
        {
            "role": "assistant",
            "content": "接下来实现 ContextConfig。",
            "timestamp": (
                datetime.now()
                - timedelta(hours=2)
            ),
        },
        {
            "role": "user",
            "content": "Gather 阶段已经运行成功。",
            "timestamp": (
                datetime.now()
                - timedelta(minutes=10)
            ),
        },
    ]

    custom_packets = [
        ContextPacket(
            content=(
                "Chapter 9 的核心流程是 GSSC。"
            ),
            timestamp=datetime.now(),
            token_count=15,
            relevance_score=0.9,
            metadata={
                "type": "custom",
                "source": "chapter9_note",
            },
        ),
        ContextPacket(
            content=(
                "Select 阶段会根据相关性和"
                "新近性筛选信息。"
            ),
            timestamp=datetime.now(),
            token_count=18,
            # 不传入 relevance_score，
            # 使用默认值 0.5，让 Select 自动计算。
            metadata={
                "type": "custom",
                "source": "select_note",
            },
        ),
        ContextPacket(
            content="今天晚饭准备吃番茄炒蛋。",
            timestamp=datetime.now(),
            token_count=12,
            # 这条信息也会自动计算相关性，
            # 预计会因为相关性过低而被过滤。
            metadata={
                "type": "custom",
                "source": "irrelevant_note",
            },
        ),
    ]

    user_query = (
        "如何实现 Chapter 9 的 Select 阶段？"
    )

    packets = builder._gather(
        user_query=user_query,
        conversation_history=conversation_history,
        system_instructions=(
            "你是一位耐心的 Python Agent 学习助手。"
        ),
        custom_packets=custom_packets,
    )

    print("\n汇集完成：")
    print(f"候选信息包数量：{len(packets)}")

    # 故意设置较小预算，
    # 方便观察 Select 的筛选效果。
    selected_packets = builder._select(
        packets=packets,
        user_query=user_query,
        available_tokens=55,
    )

    print("\n最终选中的信息包：")

    for index, packet in enumerate(
        selected_packets,
        start=1,
    ):
        print("-" * 60)
        print(f"编号：{index}")
        print(f"内容：{packet.content}")
        print(f"token 数：{packet.token_count}")
        print(
            f"相关性："
            f"{packet.relevance_score:.4f}"
        )
        print(f"元数据：{packet.metadata}")


if __name__ == "__main__":
    main()