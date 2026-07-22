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
    测试 Gather 阶段。
    """

    builder = ContextBuilder(
        config=ContextConfig(
            max_tokens=3000,
        )
    )

    # 故意准备 6 条消息。
    # Gather 最终只应保留最近 5 条。
    conversation_history = [
        {
            "role": "user",
            "content": "我准备开始学习上下文工程。",
            "timestamp": datetime.now()
            - timedelta(minutes=30),
        },
        {
            "role": "assistant",
            "content": "可以先学习 ContextPacket。",
            "timestamp": datetime.now()
            - timedelta(minutes=25),
        },
        {
            "role": "user",
            "content": "ContextPacket 已经完成。",
            "timestamp": datetime.now()
            - timedelta(minutes=20),
        },
        {
            "role": "assistant",
            "content": "接下来实现 ContextConfig。",
            "timestamp": datetime.now()
            - timedelta(minutes=15),
        },
        {
            "role": "user",
            "content": "ContextConfig 也完成了。",
            "timestamp": datetime.now()
            - timedelta(minutes=10),
        },
        {
            "role": "assistant",
            "content": "现在可以实现 Gather。",
            "timestamp": datetime.now()
            - timedelta(minutes=5),
        },
    ]

    custom_packet = ContextPacket(
        content="Chapter 9 的核心流程是 GSSC。",
        timestamp=datetime.now(),
        token_count=15,
        relevance_score=0.9,
        metadata={
            "type": "custom",
            "source": "chapter9_note",
        },
    )

    packets = builder._gather(
        user_query="接下来如何学习 Chapter 9？",
        conversation_history=conversation_history,
        system_instructions=(
            "你是一位耐心的 Python Agent 学习助手。"
        ),
        custom_packets=[custom_packet],
    )

    print("\n候选信息包：")

    for index, packet in enumerate(
        packets,
        start=1,
    ):
        print("-" * 60)
        print(f"编号：{index}")
        print(f"内容：{packet.content}")
        print(f"token 数：{packet.token_count}")
        print(
            f"相关性：{packet.relevance_score}"
        )
        print(f"元数据：{packet.metadata}")


if __name__ == "__main__":
    main()