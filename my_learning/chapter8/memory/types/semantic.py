from pathlib import Path

from ..base import BaseMemory, MemoryConfig, MemoryItem
from ..embedding import BaseEmbedding, create_embedding_model
from ..storage.json_store import JsonMemoryStorage


class SemanticMemory(BaseMemory):
    """
    Agent 的语义记忆。

    语义记忆用于保存相对稳定的事实、知识和用户偏好，例如：

    - 用户主要使用 Python 学习 Agent；
    - 用户偏好逐行解释代码；
    - Chapter 8 包含记忆系统和 RAG 系统。

    当前版本使用：

    - JSON 文件进行持久化；
    - TF-IDF 计算文本相似度；
    - metadata 保存知识分类、主题和来源。
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        storage_path: str | None = None,
        embedding_model: BaseEmbedding | None = None,
    ) -> None:
        """
        初始化语义记忆。

        config:
            记忆系统配置。

        storage_path:
            语义记忆 JSON 文件路径。

        embedding_model:
            文本嵌入模型。

            如果没有传入，则默认使用 TF-IDF。
        """

        super().__init__(config)

        if storage_path is None:
            storage_path = self._build_storage_path()

        self.storage = JsonMemoryStorage(storage_path)

        self.embedding_model = (
            embedding_model
            or create_embedding_model("tfidf")
        )

    def add(self, item: MemoryItem) -> str:
        """
        添加一条语义记忆。

        如果已经存在内容完全相同的知识，则：

        1. 保留较高的重要性；
        2. 合并 metadata；
        3. 不再创建新的记忆。
        """

        if not isinstance(item, MemoryItem):
            raise TypeError("item 必须是 MemoryItem 对象。")

        item.memory_type = "semantic"

        duplicated_item = self._find_duplicate(
            item.content
        )

        if duplicated_item is not None:
            duplicated_item.importance = max(
                duplicated_item.importance,
                item.importance,
            )

            duplicated_item.metadata.update(
                item.metadata
            )

            self.storage.update(
                duplicated_item
            )

            return duplicated_item.id

        return self.storage.add(item)

    def search(
        self,
        query: str,
        limit: int | None = None,
        min_importance: float | None = None,
        *,
        category: str | None = None,
        subject: str | None = None,
        source: str | None = None,
    ) -> list[MemoryItem]:
        """
        搜索相关语义记忆。

        query:
            查询文本。

        limit:
            最多返回多少条记忆。

        min_importance:
            只返回重要性不低于该值的记忆。

        category:
            按知识分类过滤，例如 user_preference、knowledge。

        subject:
            按主题过滤，例如 Python、Chapter 8。

        source:
            按知识来源过滤，例如 conversation、document。
        """

        self._validate_search_arguments(
            query=query,
            limit=limit,
            min_importance=min_importance,
        )

        if limit is None:
            limit = self.config.default_search_limit

        if min_importance is None:
            min_importance = self.config.min_importance

        candidate_items: list[MemoryItem] = []

        for item in self.storage.load():
            if item.importance < min_importance:
                continue

            if not self._matches_filters(
                item=item,
                category=category,
                subject=subject,
                source=source,
            ):
                continue

            candidate_items.append(item)

        if not candidate_items:
            return []

        documents = [
            item.content
            for item in candidate_items
        ]

        vector_scores = (
            self.embedding_model.similarity_scores(
                query=query,
                documents=documents,
            )
        )

        query_words = self._split_words(query)

        scored_results: list[
            tuple[float, MemoryItem]
        ] = []

        for item, vector_score in zip(
            candidate_items,
            vector_scores,
        ):
            keyword_score = (
                self._calculate_keyword_score(
                    query_words=query_words,
                    content=item.content,
                )
            )

            text_relevance = (
                vector_score * 0.8
                + keyword_score * 0.2
            )

            # 文本完全无关时，不应只依靠重要性进入结果。
            if text_relevance <= 0:
                continue

            final_score = (
                vector_score * 0.70
                + keyword_score * 0.15
                + item.importance * 0.15
            )

            scored_results.append(
                (final_score, item)
            )

        scored_results.sort(
            key=lambda result: (
                result[0],
                result[1].importance,
                result[1].created_at,
            ),
            reverse=True,
        )

        return [
            item
            for _, item in scored_results[:limit]
        ]

    def remove(self, memory_id: str) -> bool:
        """
        根据 ID 删除语义记忆。
        """

        return self.storage.remove(memory_id)

    def get_all(self) -> list[MemoryItem]:
        """
        返回全部语义记忆。
        """

        return self.storage.load()

    def clear(self) -> None:
        """
        清空全部语义记忆。
        """

        self.storage.clear()

    def get(
        self,
        memory_id: str,
    ) -> MemoryItem | None:
        """
        根据 ID 获取一条语义记忆。
        """

        return self.storage.get(memory_id)

    def update(
        self,
        item: MemoryItem,
    ) -> bool:
        """
        更新一条语义记忆。
        """

        if not isinstance(item, MemoryItem):
            raise TypeError(
                "item 必须是 MemoryItem。"
            )

        item.memory_type = "semantic"

        return self.storage.update(item)

    def _find_duplicate(
        self,
        content: str,
    ) -> MemoryItem | None:
        """
        查找内容完全相同的语义记忆。

        比较时忽略：

        - 大小写；
        - 首尾空格。
        """

        normalized_content = (
            content.strip().lower()
        )

        for item in self.storage.load():
            existing_content = (
                item.content.strip().lower()
            )

            if existing_content == normalized_content:
                return item

        return None

    @staticmethod
    def _matches_filters(
        item: MemoryItem,
        category: str | None,
        subject: str | None,
        source: str | None,
    ) -> bool:
        """
        判断一条语义记忆是否满足过滤条件。
        """

        if category is not None:
            item_category = item.metadata.get(
                "category"
            )

            if item_category != category:
                return False

        if subject is not None:
            item_subject = item.metadata.get(
                "subject"
            )

            if item_subject != subject:
                return False

        if source is not None:
            item_source = item.metadata.get(
                "source"
            )

            if item_source != source:
                return False

        return True

    @staticmethod
    def _split_words(
        text: str,
    ) -> set[str]:
        """
        将查询文本转换成关键词集合。
        """

        normalized_text = text.strip().lower()

        words = {
            word
            for word in normalized_text.split()
            if word
        }

        words.add(normalized_text)

        return words

    @staticmethod
    def _calculate_keyword_score(
        query_words: set[str],
        content: str,
    ) -> float:
        """
        计算关键词匹配分数。
        """

        if not query_words:
            return 0.0

        normalized_content = content.lower()

        matched_count = 0

        for word in query_words:
            if word in normalized_content:
                matched_count += 1

        return matched_count / len(query_words)

    @staticmethod
    def _validate_search_arguments(
        query: str,
        limit: int | None,
        min_importance: float | None,
    ) -> None:
        """
        检查搜索参数是否合法。
        """

        if not isinstance(query, str):
            raise TypeError(
                "query 必须是字符串。"
            )

        if not query.strip():
            raise ValueError(
                "query 不能为空。"
            )

        if limit is not None:
            if not isinstance(limit, int):
                raise TypeError(
                    "limit 必须是整数。"
                )

            if limit <= 0:
                raise ValueError(
                    "limit 必须大于 0。"
                )

        if min_importance is not None:
            if not isinstance(
                min_importance,
                (int, float),
            ):
                raise TypeError(
                    "min_importance 必须是数字。"
                )

            if not 0.0 <= min_importance <= 1.0:
                raise ValueError(
                    "min_importance 必须在 "
                    "0.0～1.0 之间。"
                )

    def _build_storage_path(self) -> str:
        """
        根据 config.storage_path 所在目录，
        生成 semantic_memories.json。
        """

        base_path = Path(
            self.config.storage_path
        )

        semantic_path = (
            base_path.parent
            / "semantic_memories.json"
        )

        return str(semantic_path)