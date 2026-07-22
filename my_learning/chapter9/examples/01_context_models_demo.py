import sys
from datetime import datetime
from pathlib import Path


# 将 chapter9 目录加入 Python 模块搜索路径。
CHAPTER9_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CHAPTER9_DIR))


from context import ContextConfig, ContextPacket


def main() -> None:
    """
    测试 ContextPacket 和 ContextConfig。
    """

    memory_packet = ContextPacket(
        content="用户正在学习 Hello-Agents Chapter 9。",
        timestamp=datetime.now(),
        token_count=15,
        relevance_score=0.9,
        metadata={
            "type": "memory",
            "source": "chapter8",
        },
    )

    rag_packet = ContextPacket(
        content="上下文工程需要在有限预算内选择高价值信息。",
        timestamp=datetime.now(),
        token_count=20,
        relevance_score=1.5,
        metadata={
            "type": "rag_result",
            "source": "knowledge_base",
        },
    )

    config = ContextConfig(
        max_tokens=3000,
        reserve_ratio=0.2,
        min_relevance=0.1,
        enable_compression=True,
        recency_weight=0.3,
        relevance_weight=0.7,
    )

    print("第一条信息包：")
    print(memory_packet)

    print("\n第二条信息包：")
    print(rag_packet)

    print("\n上下文配置：")
    print(config)

    print("\n自动修正后的相关性分数：")
    print(rag_packet.relevance_score)


    print("\n测试错误配置：")

    try:
        ContextConfig(
            recency_weight=0.5,
            relevance_weight=0.7,
        )
    except ValueError as error:
        print(f"成功捕获配置错误：{error}")

if __name__ == "__main__":
    main()