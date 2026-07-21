from abc import ABC, abstractmethod

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class BaseEmbedding(ABC):
    """
    文本嵌入服务的抽象基类。

    不同的嵌入实现都需要提供统一的方法：

    1. fit：根据文本集合建立向量空间；
    2. embed_text：将单条文本转换成向量；
    3. embed_documents：批量转换文本；
    4. similarity_scores：计算查询与文档的相似度。
    """

    @abstractmethod
    def fit(self, texts: list[str]) -> None:
        """
        根据文本集合建立嵌入模型。
        """

        raise NotImplementedError

    @abstractmethod
    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """
        将一条文本转换成向量。
        """

        raise NotImplementedError

    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        将多条文本批量转换成向量。
        """

        raise NotImplementedError

    @abstractmethod
    def similarity_scores(
        self,
        query: str,
        documents: list[str],
    ) -> list[float]:
        """
        计算查询与每条文档的相似度。
        """

        raise NotImplementedError


class TFIDFEmbedding(BaseEmbedding):
    """
    基于 TF-IDF 的轻量文本向量化实现。

    当前使用字符级 n-gram，原因是：

    1. 不依赖中文分词工具；
    2. 可以同时处理中文和英文；
    3. 适合作为 Chapter 8 的第一版检索实现。

    注意：
        TF-IDF 更擅长识别字面和关键词相似性，
        不等于真正的大模型语义 Embedding。
    """

    def __init__(
        self,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> None:
        """
        初始化 TF-IDF 向量化器。

        ngram_range=(1, 2) 表示同时统计：

        - 单个字符；
        - 连续两个字符。
        """

        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=ngram_range,
            lowercase=True,
            norm="l2",
        )

        self._is_fitted = False

    def fit(self, texts: list[str]) -> None:
        """
        根据文本集合建立 TF-IDF 词表和向量空间。
        """

        valid_texts = self._validate_texts(texts)

        self.vectorizer.fit(valid_texts)

        self._is_fitted = True

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """
        将一条文本转换成 TF-IDF 向量。

        调用前必须先执行 fit()。
        """

        self._ensure_fitted()
        self._validate_text(text)

        vector = self.vectorizer.transform([text])

        return vector.toarray()[0].tolist()

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        批量将文本转换成 TF-IDF 向量。

        调用前必须先执行 fit()。
        """

        self._ensure_fitted()

        valid_texts = self._validate_texts(texts)

        vectors = self.vectorizer.transform(
            valid_texts
        )

        return vectors.toarray().tolist()

    def similarity_scores(
        self,
        query: str,
        documents: list[str],
    ) -> list[float]:
        """
        计算查询文本与每条文档之间的余弦相似度。

        返回结果顺序与 documents 顺序一致。

        例如：

        documents = ["文档A", "文档B"]

        返回：

        [查询与文档A的相似度, 查询与文档B的相似度]
        """

        self._validate_text(query)

        valid_documents = self._validate_texts(
            documents
        )

        # 每次检索时，使用当前文档集合重新建立
        # TF-IDF 向量空间。
        self.fit(valid_documents)

        query_vector = self.vectorizer.transform(
            [query]
        )

        document_vectors = self.vectorizer.transform(
            valid_documents
        )

        scores = cosine_similarity(
            query_vector,
            document_vectors,
        )[0]

        return scores.tolist()

    def _ensure_fitted(self) -> None:
        """
        检查 TF-IDF 模型是否已经执行 fit()。
        """

        if not self._is_fitted:
            raise RuntimeError(
                "TFIDFEmbedding 尚未建立向量空间，"
                "请先调用 fit()。"
            )

    @staticmethod
    def _validate_text(text: str) -> None:
        """
        检查单条文本是否合法。
        """

        if not isinstance(text, str):
            raise TypeError("text 必须是字符串。")

        if not text.strip():
            raise ValueError("text 不能为空。")

    @classmethod
    def _validate_texts(
        cls,
        texts: list[str],
    ) -> list[str]:
        """
        检查文本列表是否合法。
        """

        if not isinstance(texts, list):
            raise TypeError("texts 必须是列表。")

        if not texts:
            raise ValueError("texts 不能为空列表。")

        valid_texts: list[str] = []

        for index, text in enumerate(texts):
            try:
                cls._validate_text(text)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"第 {index + 1} 条文本不合法：{error}"
                ) from error

            valid_texts.append(text.strip())

        return valid_texts


def create_embedding_model(
    model_type: str = "tfidf",
) -> BaseEmbedding:
    """
    根据模型类型创建嵌入服务。

    当前学习版只实现 TF-IDF。

    后续可以扩展：

    - dashscope；
    - local；
    - sentence-transformers。
    """

    if not isinstance(model_type, str):
        raise TypeError("model_type 必须是字符串。")

    normalized_type = model_type.strip().lower()

    if normalized_type == "tfidf":
        return TFIDFEmbedding()

    raise ValueError(
        f"暂不支持嵌入模型：{model_type}"
    )