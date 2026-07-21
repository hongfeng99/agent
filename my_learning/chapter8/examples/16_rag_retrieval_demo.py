import sys
from pathlib import Path


CHAPTER8_DIR = (
    Path(__file__).resolve().parents[1]
)

if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(CHAPTER8_DIR),
    )


from memory import create_embedding_model
from memory.rag import (
    DocumentProcessor,
    RAGPipeline,
)


DOCUMENT_PATH = (
    CHAPTER8_DIR
    / "knowledge_base"
    / "chapter8_notes.md"
)


def print_results(
    query: str,
    results: list,
) -> None:
    """
    打印一次查询的检索结果。
    """

    print("\n" + "=" * 70)
    print(f"查询：{query}")
    print("=" * 70)

    if not results:
        print("没有找到满足条件的文本块。")
        return

    for result in results:
        document = result.document

        print(
            f"\n排名：{result.rank}"
        )

        print(
            f"相似度："
            f"{result.score:.4f}"
        )

        print(
            f"来源文件："
            f"{document.metadata.get('file_name')}"
        )

        print(
            f"文本块序号："
            f"{document.metadata.get('chunk_index')}"
        )

        print(
            f"字符范围："
            f"{document.metadata.get('start_index')}"
            f"～"
            f"{document.metadata.get('end_index')}"
        )

        print("文本内容：")
        print(document.content)

        print("-" * 70)


def main() -> None:
    # 1. 创建文档处理器
    processor = DocumentProcessor(
        chunk_size=150,
        chunk_overlap=30,
    )

    # 2. 创建 TF-IDF 嵌入模型
    embedding_model = (
        create_embedding_model(
            model_type="tfidf"
        )
    )

    # 3. 创建 RAG 检索管线
    pipeline = RAGPipeline(
        document_processor=processor,
        embedding_model=embedding_model,
    )

    print("=" * 70)
    print("1. 添加文档到 RAG 知识库")
    print("=" * 70)

    chunks = pipeline.add_file(
        str(DOCUMENT_PATH)
    )

    print(
        f"本次生成文本块数量："
        f"{len(chunks)}"
    )

    print(
        f"知识库文本块总数："
        f"{pipeline.document_count}"
    )

    print("\nRAG 统计信息：")

    for key, value in (
        pipeline.stats().items()
    ):
        print(f"- {key}: {value}")

    # 4. 查询工作记忆
    query_1 = (
        "工作记忆为什么需要生存时间？"
    )

    results_1 = pipeline.search(
        query=query_1,
        top_k=3,
    )

    print_results(
        query_1,
        results_1,
    )

    # 5. 查询 RAG 流程
    query_2 = (
        "RAG 的数据准备阶段包括什么？"
    )

    results_2 = pipeline.search(
        query=query_2,
        top_k=3,
    )

    print_results(
        query_2,
        results_2,
    )

    # 6. 测试无关问题
    query_3 = (
        "如何种植苹果树？"
    )

    results_3 = pipeline.search(
        query=query_3,
        top_k=3,
        min_score=0.01,
    )

    print_results(
        query_3,
        results_3,
    )


if __name__ == "__main__":
    main()