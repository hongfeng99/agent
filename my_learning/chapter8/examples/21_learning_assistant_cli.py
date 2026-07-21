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

from assistant import LearningAssistant
from memory import create_embedding_model
from memory.manager import MemoryManager
from memory.rag import (
    DocumentProcessor,
    RAGPipeline,
)
from memory.types.episodic import (
    EpisodicMemory,
)
from memory.types.semantic import (
    SemanticMemory,
)
from memory.types.working import (
    WorkingMemory,
)
from tools.memory_tool import MemoryTool
from tools.rag_tool import RAGTool


DATA_DIR = CHAPTER8_DIR / "data"
REPORT_DIR = CHAPTER8_DIR / "reports"

DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


def create_memory_tool() -> MemoryTool:
    """
    创建记忆工具。
    """

    memory_manager = MemoryManager(
        memories={
            "working": WorkingMemory(),
            "episodic": EpisodicMemory(
                storage_path=str(
                    DATA_DIR
                    / "assistant_episodic.json"
                ),
            ),
            "semantic": SemanticMemory(
                storage_path=str(
                    DATA_DIR
                    / "assistant_semantic.json"
                ),
            ),
        }
    )

    return MemoryTool(
        manager=memory_manager
    )


def create_rag_tool() -> RAGTool:
    """
    创建 RAG 工具。
    """

    llm = HelloAgentsLLM()

    processor = DocumentProcessor(
        chunk_size=300,
        chunk_overlap=60,
    )

    embedding_model = (
        create_embedding_model(
            model_type="tfidf"
        )
    )

    pipeline = RAGPipeline(
        document_processor=processor,
        embedding_model=embedding_model,
        llm=llm,
    )

    return RAGTool(
        pipeline=pipeline
    )


def print_result(
    result: object,
) -> None:
    """
    以 JSON 形式打印执行结果。
    """

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def print_menu() -> None:
    print("\n" + "=" * 60)
    print("Chapter 8 Learning Assistant")
    print("=" * 60)
    print("1. 加载文档")
    print("2. 向文档提问")
    print("3. 添加学习笔记")
    print("4. 回顾学习记录")
    print("5. 查看学习统计")
    print("6. 生成学习报告")
    print("0. 退出")


def main() -> None:
    assistant = LearningAssistant(
        memory_tool=create_memory_tool(),
        rag_tool=create_rag_tool(),
        report_dir=REPORT_DIR,
        user_id="chapter8_user",
    )

    print("学习助手初始化完成。")

    while True:
        print_menu()

        choice = input(
            "\n请输入操作编号："
        ).strip()

        try:
            if choice == "1":
                file_path = input(
                    "请输入 txt 或 md 文件路径："
                ).strip()

                result = (
                    assistant.load_document(
                        file_path
                    )
                )

                print_result(result)

            elif choice == "2":
                question = input(
                    "请输入问题："
                ).strip()

                result = assistant.ask(
                    question=question,
                    top_k=3,
                    min_score=0.01,
                )

                print_result(result)

            elif choice == "3":
                note = input(
                    "请输入学习笔记："
                ).strip()

                result = assistant.add_note(
                    note
                )

                print_result(result)

            elif choice == "4":
                query = input(
                    "请输入要回顾的内容："
                ).strip()

                result = assistant.recall(
                    query=query,
                    limit=5,
                )

                print_result(result)

            elif choice == "5":
                result = assistant.get_stats()

                print_result(result)

            elif choice == "6":
                result = (
                    assistant.generate_report(
                        save_to_file=True
                    )
                )

                print_result(result)

            elif choice == "0":
                print("学习助手已退出。")
                break

            else:
                print("请输入 0～6 之间的编号。")

        except Exception as error:
            print(
                f"操作失败："
                f"{type(error).__name__}: "
                f"{error}"
            )


if __name__ == "__main__":
    main()