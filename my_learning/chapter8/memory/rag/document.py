from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class Document:
    """
    RAG 系统中的文档对象。

    一份完整文档和文档切分后产生的文本块，
    都可以使用 Document 表示。
    """

    content: str

    document_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        创建 Document 后自动检查数据是否合法。
        """

        if not isinstance(self.content, str):
            raise TypeError("content 必须是字符串。")

        self.content = self.content.strip()

        if not self.content:
            raise ValueError("content 不能为空。")

        if not isinstance(self.document_id, str):
            raise TypeError(
                "document_id 必须是字符串。"
            )

        self.document_id = self.document_id.strip()

        if not self.document_id:
            raise ValueError(
                "document_id 不能为空。"
            )

        if not isinstance(self.metadata, dict):
            raise TypeError(
                "metadata 必须是字典。"
            )


class DocumentProcessor:
    """
    简单文档处理器。

    第一版实现以下功能：

    1. 读取 txt 和 md 文档；
    2. 将长文本切分为多个文本块；
    3. 为每个文本块保存来源和序号；
    4. 支持相邻文本块之间保留重叠内容。
    """

    SUPPORTED_SUFFIXES = {
        ".txt",
        ".md",
    }

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ) -> None:
        """
        chunk_size:
            每个文本块最多包含多少个字符。

        chunk_overlap:
            相邻文本块重复保留多少个字符。
        """

        if not isinstance(chunk_size, int):
            raise TypeError(
                "chunk_size 必须是整数。"
            )

        if not isinstance(chunk_overlap, int):
            raise TypeError(
                "chunk_overlap 必须是整数。"
            )

        if chunk_size <= 0:
            raise ValueError(
                "chunk_size 必须大于 0。"
            )

        if chunk_overlap < 0:
            raise ValueError(
                "chunk_overlap 不能小于 0。"
            )

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap 必须小于 chunk_size。"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_file(
        self,
        file_path: str | Path,
    ) -> Document:
        """
        读取一个 txt 或 md 文件，
        返回一份完整的 Document。
        """

        path = Path(file_path).resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"文件不存在：{path}"
            )

        if not path.is_file():
            raise ValueError(
                f"路径不是文件：{path}"
            )

        suffix = path.suffix.lower()

        if suffix not in self.SUPPORTED_SUFFIXES:
            raise ValueError(
                f"暂不支持该文件格式：{suffix}。"
                f"当前支持："
                f"{sorted(self.SUPPORTED_SUFFIXES)}"
            )

        try:
            content = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError as error:
            raise ValueError(
                f"文件不是 UTF-8 编码：{path}"
            ) from error

        return Document(
            content=content,
            metadata={
                "source": str(path),
                "file_name": path.name,
                "file_type": suffix,
            },
        )

    def split_text(
        self,
        text: str,
        *,
        source_document_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[Document]:
        """
        将一段长文本切分为多个 Document。

        采用滑动窗口：

        第一个文本块：
            text[0:chunk_size]

        第二个文本块：
            从 chunk_size - chunk_overlap 开始

        因此相邻文本块之间存在重叠部分。
        """

        if not isinstance(text, str):
            raise TypeError(
                "text 必须是字符串。"
            )

        cleaned_text = text.strip()

        if not cleaned_text:
            raise ValueError(
                "text 不能为空。"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata 必须是字典。"
            )

        if source_document_id is None:
            source_document_id = str(uuid4())

        step = (
            self.chunk_size
            - self.chunk_overlap
        )

        chunks: list[Document] = []

        start = 0
        chunk_index = 0
        text_length = len(cleaned_text)

        while start < text_length:
            end = min(
                start + self.chunk_size,
                text_length,
            )

            chunk_content = cleaned_text[
                start:end
            ].strip()

            if chunk_content:
                chunk_metadata = {
                    **metadata,
                    "source_document_id":
                        source_document_id,
                    "chunk_index":
                        chunk_index,
                    "start_index":
                        start,
                    "end_index":
                        end,
                }

                chunk = Document(
                    content=chunk_content,
                    document_id=(
                        f"{source_document_id}"
                        f"_chunk_{chunk_index}"
                    ),
                    metadata=chunk_metadata,
                )

                chunks.append(chunk)

                chunk_index += 1

            if end >= text_length:
                break

            start += step

        return chunks

    def process_file(
        self,
        file_path: str | Path,
    ) -> list[Document]:
        """
        完整处理一个文件：

        读取文件
            ↓
        获得完整文档
            ↓
        切分为多个文本块
        """

        document = self.load_file(file_path)

        return self.split_text(
            text=document.content,
            source_document_id=(
                document.document_id
            ),
            metadata=document.metadata,
        )