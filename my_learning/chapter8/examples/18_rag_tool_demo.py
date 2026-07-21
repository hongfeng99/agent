import json
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
    RAGPipeline,
)

from tools.rag_tool import RAGTool


DOCUMENT_PATH = (
    CHAPTER8_DIR
    / "knowledge_base"
    / "chapter8_notes.md"
)


def print_tool_result(
    title: str,
    result_text: str,
) -> None:
    """
    以便于阅读的形式打印工具结果。
    """

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    try:
        result_data = json.loads(
            result_text
        )

        print(
            json.dumps(
                result_data,
                ensure_ascii=False,
                indent=2,
            )
        )

    except json.JSONDecodeError:
        print(result_text)


def main() -> None:
    if not DOCUMENT_PATH.exists():
        raise FileNotFoundError(
            f"测试文档不存在：{DOCUMENT_PATH}"
        )

    # 1. 创建文档处理器
    document_processor = (
        DocumentProcessor(
            chunk_size=150,
            chunk_overlap=30,
        )
    )

    # 2. 创建 TF-IDF 嵌入模型
    embedding_model = (
        create_embedding_model(
            model_type="tfidf"
        )
    )

    # 3. 创建大模型
    llm = HelloAgentsLLM()

    # 4. 创建 RAG 管线
    pipeline = RAGPipeline(
        document_processor=(
            document_processor
        ),
        embedding_model=embedding_model,
        llm=llm,
    )

    # 5. 创建 RAG 工具
    rag_tool = RAGTool(
        pipeline=pipeline
    )

    print("=" * 70)
    print("RAGTool 创建成功")
    print("=" * 70)

    print(f"工具名称：{rag_tool.name}")
    print(f"工具说明：\n{rag_tool.description}")

    # 6. 添加文件
    add_file_result = rag_tool.execute(
        "add_file",
        file_path=str(DOCUMENT_PATH),
    )

    print_tool_result(
        "1. 添加知识文件",
        add_file_result,
    )

    # 7. 添加一段额外文本
    add_text_result = rag_tool.execute(
        "add_text",
        text=(
            "MemoryTool 负责保存和检索"
            "智能体的历史交互信息。"
            "RAGTool 负责从外部知识库中"
            "检索资料并生成答案。"
        ),
        metadata={
            "source": "manual_text",
            "file_name": "manual_text",
            "category": "agent_tools",
        },
    )

    print_tool_result(
        "2. 添加文本知识",
        add_text_result,
    )

    # 8. 检索知识
    search_result = rag_tool.execute(
        "search",
        query="工作记忆有什么特点？",
        top_k=3,
        min_score=0.01,
    )

    print_tool_result(
        "3. 检索工作记忆相关知识",
        search_result,
    )

    # 9. 根据知识库回答问题
    ask_result = rag_tool.execute(
        "ask",
        question=(
            "MemoryTool 和 RAGTool "
            "分别负责什么？"
        ),
        top_k=3,
        min_score=0.01,
        temperature=0,
        max_tokens=1000,
    )

    print_tool_result(
        "4. 根据知识库生成答案",
        ask_result,
    )

    # 10. 查看统计信息
    stats_result = rag_tool.execute(
        "stats"
    )

    print_tool_result(
        "5. 查看知识库统计",
        stats_result,
    )

    # 11. 测试错误处理
    invalid_result = rag_tool.execute(
        "unknown_action"
    )

    print_tool_result(
        "6. 测试未知 action",
        invalid_result,
    )

    # 本次暂不清空，
    # 方便观察 pipeline 中的数据。
    #
    # 由于当前 RAGPipeline 是纯内存存储，
    # 程序退出后数据本身也不会持久化。


if __name__ == "__main__":
    main()