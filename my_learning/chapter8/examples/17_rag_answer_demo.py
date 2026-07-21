import sys
from pathlib import Path


CHAPTER8_DIR = (
    Path(__file__).resolve().parents[1]
)

CHAPTER7_DIR = (
    CHAPTER8_DIR.parent / "chapter7"
)

if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(CHAPTER8_DIR),
    )

if str(CHAPTER7_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(CHAPTER7_DIR),
    )


from hello_agents import HelloAgentsLLM

from memory import create_embedding_model
from memory.rag import (
    DocumentProcessor,
    RAGAnswer,
    RAGPipeline,
)


DOCUMENT_PATH = (
    CHAPTER8_DIR
    / "knowledge_base"
    / "chapter8_notes.md"
)


def print_rag_answer(
    result: RAGAnswer,
) -> None:
    """
    打印 RAG 最终答案以及检索依据。
    """

    print("\n" + "=" * 70)
    print("用户问题")
    print("=" * 70)
    print(result.question)

    print("\n" + "=" * 70)
    print("RAG 最终回答")
    print("=" * 70)
    print(result.answer)

    print("\n" + "=" * 70)
    print("本次回答使用的检索结果")
    print("=" * 70)

    if not result.retrieval_results:
        print("没有使用任何检索资料。")
        return

    for retrieval_result in (
        result.retrieval_results
    ):
        document = retrieval_result.document

        print(
            f"\n排名："
            f"{retrieval_result.rank}"
        )

        print(
            f"相似度："
            f"{retrieval_result.score:.4f}"
        )

        print(
            f"来源文件："
            f"{document.metadata.get('file_name')}"
        )

        print(
            f"文本块序号："
            f"{document.metadata.get('chunk_index')}"
        )

        print("文本块内容：")
        print(document.content)

        print("-" * 70)


def main() -> None:
    # 1. 创建文档处理器
    document_processor = DocumentProcessor(
        chunk_size=150,
        chunk_overlap=30,
    )

    # 2. 创建 TF-IDF 嵌入模型
    embedding_model = (
        create_embedding_model(
            model_type="tfidf"
        )
    )

    # 3. 创建大模型客户端
    llm = HelloAgentsLLM()

    # 4. 创建完整 RAG 管线
    pipeline = RAGPipeline(
        document_processor=document_processor,
        embedding_model=embedding_model,
        llm=llm,
    )

    # 5. 将文档加入知识库
    chunks = pipeline.add_file(
        str(DOCUMENT_PATH)
    )

    print("=" * 70)
    print("知识库初始化完成")
    print("=" * 70)

    print(
        f"加载文件：{DOCUMENT_PATH.name}"
    )

    print(
        f"文本块数量：{len(chunks)}"
    )

    # 6. 第一个问题
    result_1 = pipeline.ask(
        question=(
            "工作记忆和情景记忆"
            "分别有什么特点？"
        ),
        top_k=3,
        min_score=0.01,
        temperature=0,
    )

    print_rag_answer(result_1)

    # 7. 第二个问题
    result_2 = pipeline.ask(
        question=(
            "RAG 的完整处理流程是什么？"
        ),
        top_k=3,
        min_score=0.01,
        temperature=0,
    )

    print_rag_answer(result_2)

    # 8. 测试知识库以外的问题
    result_3 = pipeline.ask(
        question=(
            "苹果树应该在什么季节修剪？"
        ),
        top_k=3,
        min_score=0.05,
        temperature=0,
    )

    print_rag_answer(result_3)


if __name__ == "__main__":
    main()