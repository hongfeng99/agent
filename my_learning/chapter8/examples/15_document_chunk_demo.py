import sys
from pathlib import Path


CHAPTER8_DIR = Path(__file__).resolve().parents[1]

if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(CHAPTER8_DIR),
    )


from memory.rag.document import (
    DocumentProcessor,
)


KNOWLEDGE_BASE_DIR = (
    CHAPTER8_DIR / "knowledge_base"
)

DOCUMENT_PATH = (
    KNOWLEDGE_BASE_DIR
    / "chapter8_notes.md"
)


def main() -> None:
    processor = DocumentProcessor(
        chunk_size=150,
        chunk_overlap=30,
    )

    print("=" * 70)
    print("1. 读取完整文档")
    print("=" * 70)

    document = processor.load_file(
        DOCUMENT_PATH
    )

    print(
        f"文档 ID：{document.document_id}"
    )
    print(
        f"文件名称："
        f"{document.metadata['file_name']}"
    )
    print(
        f"文档字符数：{len(document.content)}"
    )
    print(
        f"文档来源："
        f"{document.metadata['source']}"
    )

    print("\n" + "=" * 70)
    print("2. 对文档进行分块")
    print("=" * 70)

    chunks = processor.process_file(
        DOCUMENT_PATH
    )

    print(
        f"总共生成 {len(chunks)} 个文本块。"
    )

    for chunk in chunks:
        print("\n" + "-" * 70)

        print(
            f"文本块 ID："
            f"{chunk.document_id}"
        )

        print(
            f"文本块序号："
            f"{chunk.metadata['chunk_index']}"
        )

        print(
            f"字符范围："
            f"{chunk.metadata['start_index']}"
            f"～"
            f"{chunk.metadata['end_index']}"
        )

        print(
            f"文本块长度："
            f"{len(chunk.content)}"
        )

        print("文本内容：")
        print(chunk.content)

    print("\n" + "=" * 70)
    print("3. 检查相邻文本块的重叠部分")
    print("=" * 70)

    if len(chunks) >= 2:
        first_chunk_tail = (
            chunks[0].content[-30:]
        )

        second_chunk_head = (
            chunks[1].content[:30]
        )

        print("第一个文本块最后 30 个字符：")
        print(first_chunk_tail)

        print("\n第二个文本块最前 30 个字符：")
        print(second_chunk_head)

        print(
            "\n两部分是否相同：",
            first_chunk_tail
            == second_chunk_head,
        )


if __name__ == "__main__":
    main()