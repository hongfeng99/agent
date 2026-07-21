from dataclasses import dataclass
from typing import Any

from memory import create_embedding_model
from memory.rag.document import (
    Document,
    DocumentProcessor,
)


@dataclass
class RetrievalResult:
    """
    表示一条 RAG 检索结果。

    document:
        被检索到的文本块。

    score:
        查询与文本块之间的相似度。

    rank:
        当前结果的排名，从 1 开始。
    """

    document: Document
    score: float
    rank: int

@dataclass
class RAGAnswer:
    """
    表示一次完整的 RAG 问答结果。

    question:
        用户原始问题。

    answer:
        大模型基于检索资料生成的答案。

    retrieval_results:
        本次使用的检索结果。

    context:
        实际提供给大模型的参考资料。
    """

    question: str
    answer: str
    retrieval_results: list[RetrievalResult]
    context: str


class RAGPipeline:
    """
    第一版基础 RAG 检索管线。

    当前负责：

    1. 读取和切分文档；
    2. 保存文本块；
    3. 使用 TF-IDF 计算相似度；
    4. 返回相关性最高的文本块。

    当前暂时不负责：

    1. 调用大语言模型；
    2. 生成最终答案；
    3. 向量持久化；
    4. 使用 Qdrant 等向量数据库。
    """

    def __init__(
        self,
        document_processor: DocumentProcessor | None = None,
        embedding_model: Any | None = None,
        llm: Any | None = None,
    ) -> None:
        """
        初始化 RAG 检索管线。

        document_processor:
            文档读取和分块器。

        embedding_model:
            文本嵌入模型。
            没有传入时，默认使用 TF-IDF。
        """

        self.document_processor = (
            document_processor
            or DocumentProcessor()
        )

        self.embedding_model = (
            embedding_model
            or create_embedding_model(
                model_type="tfidf"
            )
        )

        # 第一版直接把文本块保存在内存中。
        self._documents: list[Document] = []

        self.llm = llm

    @property
    def document_count(self) -> int:
        """
        返回当前保存的文本块数量。
        """

        return len(self._documents)

    def add_documents(
        self,
        documents: list[Document],
    ) -> int:
        """
        把多个 Document 添加到知识库。

        返回本次实际新增的文本块数量。
        """

        if not isinstance(documents, list):
            raise TypeError(
                "documents 必须是列表。"
            )

        existing_ids = {
            document.document_id
            for document in self._documents
        }

        added_count = 0

        for document in documents:
            if not isinstance(
                document,
                Document,
            ):
                raise TypeError(
                    "documents 中的每个元素"
                    "都必须是 Document。"
                )

            # 同一个 document_id 不重复添加。
            if (
                document.document_id
                in existing_ids
            ):
                continue

            self._documents.append(document)

            existing_ids.add(
                document.document_id
            )

            added_count += 1

        return added_count

    def add_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Document]:
        """
        直接添加一段文本。

        文本会先被切分，再加入知识库。
        """

        chunks = (
            self.document_processor.split_text(
                text=text,
                metadata=metadata,
            )
        )

        self.add_documents(chunks)

        return chunks

    def add_file(
        self,
        file_path: str,
    ) -> list[Document]:
        """
        读取并添加一个 txt 或 md 文件。

        执行流程：

        文件
        → 完整文档
        → 文本分块
        → 加入内存知识库
        """

        chunks = (
            self.document_processor.process_file(
                file_path
            )
        )

        self.add_documents(chunks)

        return chunks

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        """
        搜索和查询内容最相关的文本块。

        query:
            用户查询。

        top_k:
            最多返回多少条结果。

        min_score:
            最低相似度要求。
        """

        if not isinstance(query, str):
            raise TypeError(
                "query 必须是字符串。"
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "query 不能为空。"
            )

        if not isinstance(top_k, int):
            raise TypeError(
                "top_k 必须是整数。"
            )

        if top_k <= 0:
            raise ValueError(
                "top_k 必须大于 0。"
            )

        if not isinstance(
            min_score,
            (int, float),
        ):
            raise TypeError(
                "min_score 必须是数值。"
            )

        if min_score < 0:
            raise ValueError(
                "min_score 不能小于 0。"
            )

        if not self._documents:
            return []

        document_contents = [
            document.content
            for document in self._documents
        ]

        # 复用之前已经完成的 TF-IDF 接口。
        scores = (
            self.embedding_model
            .similarity_scores(
                query=query,
                documents=document_contents,
            )
        )

        if len(scores) != len(
            self._documents
        ):
            raise RuntimeError(
                "相似度数量和文本块数量不一致。"
            )

        document_score_pairs = list(
            zip(
                self._documents,
                scores,
            )
        )

        # 相似度从高到低排序。
        document_score_pairs.sort(
            key=lambda item: float(item[1]),
            reverse=True,
        )

        results: list[RetrievalResult] = []

        for document, score in (
            document_score_pairs
        ):
            numeric_score = float(score)

            if numeric_score < min_score:
                continue

            result = RetrievalResult(
                document=document,
                score=numeric_score,
                rank=len(results) + 1,
            )

            results.append(result)

            if len(results) >= top_k:
                break

        return results

    def get_all_documents(
        self,
    ) -> list[Document]:
        """
        返回当前知识库中的所有文本块。

        使用 list() 创建副本，
        避免外部直接修改内部列表。
        """

        return list(self._documents)

    def clear(self) -> int:
        """
        清空知识库。

        返回清空前的文本块数量。
        """

        old_count = len(self._documents)

        self._documents.clear()

        return old_count

    def stats(self) -> dict[str, Any]:
        """
        返回当前 RAG 管线统计信息。
        """

        source_files = {
            document.metadata.get(
                "source",
                "unknown",
            )
            for document in self._documents
        }

        return {
            "document_count":
                len(self._documents),
            "source_count":
                len(source_files),
            "sources":
                sorted(source_files),
            "embedding_model":
                type(
                    self.embedding_model
                ).__name__,
            "chunk_size":
                self.document_processor
                .chunk_size,
            "chunk_overlap":
                self.document_processor
                .chunk_overlap,
        }
    
    def build_context(
        self,
        results: list[RetrievalResult],
    ) -> str:
        """
        把多条检索结果拼接成可提供给大模型的上下文。
        """

        if not isinstance(results, list):
            raise TypeError(
                "results 必须是列表。"
            )

        if not results:
            return ""

        context_parts: list[str] = []

        for result in results:
            if not isinstance(
                result,
                RetrievalResult,
            ):
                raise TypeError(
                    "results 中的每个元素"
                    "都必须是 RetrievalResult。"
                )

            document = result.document

            file_name = document.metadata.get(
                "file_name",
                "未知来源",
            )

            chunk_index = document.metadata.get(
                "chunk_index",
                "未知",
            )

            context_part = (
                f"[参考资料 {result.rank}]\n"
                f"来源文件：{file_name}\n"
                f"文本块序号：{chunk_index}\n"
                f"相关度：{result.score:.4f}\n"
                f"内容：\n"
                f"{document.content}"
            )

            context_parts.append(context_part)

        return "\n\n".join(context_parts)



    def ask(
        self,
        question: str,
        top_k: int = 3,
        min_score: float = 0.01,
        temperature: float = 0,
        max_tokens: int = 1000,
    ) -> RAGAnswer:
        """
        根据知识库回答问题。

        执行过程：

        1. 检索相关文本块；
        2. 构建参考上下文；
        3. 构建消息列表；
        4. 调用大模型；
        5. 返回答案和检索依据。
        """

        if not isinstance(question, str):
            raise TypeError(
                "question 必须是字符串。"
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "question 不能为空。"
            )

        if self.llm is None:
            raise RuntimeError(
                "当前 RAGPipeline 没有配置 llm，"
                "无法生成答案。"
            )

        # 第一步：检索相关资料
        results = self.search(
            query=question,
            top_k=top_k,
            min_score=min_score,
        )

        # 没有找到合格资料时，不调用大模型。
        if not results:
            return RAGAnswer(
                question=question,
                answer=(
                    "当前知识库中没有找到"
                    "足以回答该问题的相关资料。"
                ),
                retrieval_results=[],
                context="",
            )

        # 第二步：拼接检索上下文
        context = self.build_context(results)

        # 第三步：构建发送给模型的消息
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一名严谨的文档问答助手。"
                    "你只能根据用户提供的参考资料回答。"
                    "不能使用参考资料之外的知识进行补充。"
                    "如果参考资料不足以回答问题，"
                    "必须明确说明资料不足。"
                    "回答时应尽量清晰、准确、简洁。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"请根据下面的参考资料回答问题。\n\n"
                    f"{context}\n\n"
                    f"用户问题：\n"
                    f"{question}\n\n"
                    f"回答要求：\n"
                    f"1. 只根据参考资料回答；\n"
                    f"2. 不要编造资料中没有的信息；\n"
                    f"3. 回答最后注明使用了哪些参考资料编号。"
                ),
            },
        ]

        # 第四步：调用大模型生成答案
        answer = self.llm.invoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not isinstance(answer, str):
            answer = str(answer)

        answer = answer.strip()

        if not answer:
            answer = "模型没有返回有效答案。"

        # 第五步：返回答案及检索证据
        return RAGAnswer(
            question=question,
            answer=answer,
            retrieval_results=results,
            context=context,
        )