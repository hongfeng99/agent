from datetime import datetime, timedelta

from ..base import BaseMemory, MemoryConfig, MemoryItem
from ..embedding import BaseEmbedding, create_embedding_model


class WorkingMemory(BaseMemory):
    """
    Agent 的工作记忆。

    工作记忆具有以下特点：

    1. 使用 Python 列表保存在内存中；
    2. 程序结束后数据会消失；
    3. 有最大容量限制；
    4. 记忆超过 TTL 后自动过期；
    5. 支持关键词搜索；
    6. 搜索结果按相关性、重要性和时间排序。
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        embedding_model: BaseEmbedding | None = None,
    ) -> None:
        """
        初始化工作记忆。

        config:
            记忆系统配置。

        embedding_model:
            文本嵌入模型。

            如果没有传入，就默认创建 TF-IDF 嵌入模型。
        """

        super().__init__(config)

        # 使用列表保存工作记忆
        self.memories: list[MemoryItem] = []

        # 默认使用 TF-IDF 进行文本相似度计算
        self.embedding_model = (
            embedding_model
            or create_embedding_model("tfidf")
        )

    def add(self, item: MemoryItem) -> str:
        """
        添加一条工作记忆。

        执行步骤：

        1. 检查 item 是否为 MemoryItem；
        2. 将记忆类型设置为 working；
        3. 清理已经过期的记忆；
        4. 检查是否存在重复内容；
        5. 将新记忆加入列表；
        6. 如果超过容量，移除价值最低的记忆；
        7. 返回记忆 ID。
        """

        if not isinstance(item, MemoryItem):
            raise TypeError("item 必须是 MemoryItem 对象。")

        # WorkingMemory 中的记忆统一标记为 working
        item.memory_type = "working"

        # 添加新记忆前，先清理过期内容
        self.cleanup_expired()

        # 检查是否已经存在内容完全相同的记忆
        duplicated_item = self._find_duplicate(item.content)

        if duplicated_item is not None:
            # 如果内容重复，则不再添加新对象，
            # 而是更新旧记忆的重要性和时间。
            duplicated_item.importance = max(
                duplicated_item.importance,
                item.importance,
            )

            duplicated_item.created_at = datetime.now()

            # 将新 metadata 合并到原来的 metadata 中
            duplicated_item.metadata.update(item.metadata)

            return duplicated_item.id

        self.memories.append(item)

        # 确保工作记忆数量没有超过最大容量
        self._enforce_capacity()

        return item.id

    def search(
        self,
        query: str,
        limit: int | None = None,
        min_importance: float | None = None,
    ) -> list[MemoryItem]:
        """
        搜索与查询相关的工作记忆。

        综合考虑：

        1. TF-IDF 文本相似度；
        2. 关键词匹配程度；
        3. 记忆重要性；
        4. 记忆时间衰减。
        """

        if not isinstance(query, str):
            raise TypeError("query 必须是字符串。")

        if not query.strip():
            raise ValueError("query 不能为空。")

        if limit is None:
            limit = self.config.default_search_limit

        if min_importance is None:
            min_importance = self.config.min_importance

        if not isinstance(limit, int):
            raise TypeError("limit 必须是整数。")

        if limit <= 0:
            raise ValueError("limit 必须大于 0。")

        if not isinstance(
            min_importance,
            (int, float),
        ):
            raise TypeError(
                "min_importance 必须是数字。"
            )

        if not 0.0 <= min_importance <= 1.0:
            raise ValueError(
                "min_importance 必须在 0.0～1.0 之间。"
            )

        # 搜索前先删除过期记忆
        self.cleanup_expired()

        # 先根据重要性进行初步过滤
        candidate_items = [
            item
            for item in self.memories
            if item.importance >= min_importance
        ]

        if not candidate_items:
            return []

        candidate_documents = [
            item.content
            for item in candidate_items
        ]

        # 计算查询与所有候选记忆的 TF-IDF 相似度
        vector_scores = (
            self.embedding_model.similarity_scores(
                query=query,
                documents=candidate_documents,
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

            # TF-IDF 占 70%，关键词匹配占 30%
            base_relevance = (
                vector_score * 0.7
                + keyword_score * 0.3
            )

            # 如果完全不相关，则不返回
            if base_relevance <= 0:
                continue

            time_decay = self._calculate_time_decay(
                item
            )

            # 重要性调整系数范围约为 0.8～1.2
            importance_factor = (
                0.8 + item.importance * 0.4
            )

            final_score = (
                base_relevance
                * time_decay
                * importance_factor
            )

            scored_results.append(
                (final_score, item)
            )

        scored_results.sort(
            key=lambda result: (
                result[0],
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
        根据 ID 删除一条工作记忆。
        """

        if not isinstance(memory_id, str):
            raise TypeError("memory_id 必须是字符串。")

        if not memory_id.strip():
            raise ValueError("memory_id 不能为空。")

        for index, item in enumerate(self.memories):
            if item.id == memory_id:
                self.memories.pop(index)
                return True

        return False

    def get_all(self) -> list[MemoryItem]:
        """
        返回当前所有没有过期的工作记忆。

        返回列表副本，避免外部代码直接修改内部列表。
        """

        self.cleanup_expired()

        return self.memories.copy()

    def clear(self) -> None:
        """
        清空全部工作记忆。
        """

        self.memories.clear()

    def cleanup_expired(self) -> int:
        """
        清理超过 TTL 的工作记忆。

        返回：
            被删除的记忆数量。
        """

        ttl = timedelta(
            minutes=self.config.working_memory_ttl_minutes
        )

        current_time = datetime.now()

        valid_memories = []

        for item in self.memories:
            memory_age = current_time - item.created_at

            if memory_age <= ttl:
                valid_memories.append(item)

        removed_count = (
            len(self.memories) - len(valid_memories)
        )

        self.memories = valid_memories

        return removed_count

    def _find_duplicate(
        self,
        content: str,
    ) -> MemoryItem | None:
        """
        查找内容完全相同的记忆。

        比较前会：
        - 去除首尾空格；
        - 转换成小写。
        """

        normalized_content = content.strip().lower()

        for item in self.memories:
            if (
                item.content.strip().lower()
                == normalized_content
            ):
                return item

        return None

    def _enforce_capacity(self) -> None:
        """
        保证工作记忆数量不超过容量上限。

        如果超过容量，优先删除：

        1. 重要性最低的记忆；
        2. 重要性相同时，删除最早创建的记忆。
        """

        capacity = self.config.working_memory_capacity

        while len(self.memories) > capacity:
            lowest_value_item = min(
                self.memories,
                key=lambda item: (
                    item.importance,
                    item.created_at,
                ),
            )

            self.memories.remove(lowest_value_item)

    @staticmethod
    def _split_words(text: str) -> set[str]:
        """
        将文本转换为简单的搜索词集合。

        当前版本主要按照空格进行分割。

        对于英文句子效果较好；
        对于中文，还会保留整个查询字符串进行匹配。
        """

        normalized_text = text.strip().lower()

        words = {
            word
            for word in normalized_text.split()
            if word
        }

        # 中文文本可能没有空格，因此保留完整字符串
        words.add(normalized_text)

        return words

    @staticmethod
    def _calculate_keyword_score(
        query_words: set[str],
        content: str,
    ) -> float:
        """
        计算查询关键词与记忆内容之间的匹配程度。

        返回值范围为 0.0～1.0。
        """

        if not query_words:
            return 0.0

        normalized_content = content.lower()

        matched_count = 0

        for word in query_words:
            if word in normalized_content:
                matched_count += 1

        return matched_count / len(query_words)
    


    def _calculate_time_decay(
        self,
        item: MemoryItem,
    ) -> float:
        """
        根据记忆存在时间计算时间衰减系数。

        越新的记忆，系数越接近 1.0；
        越接近 TTL，系数越接近 0.5。

        已经过期的记忆会在搜索前被清理。
        """

        current_time = datetime.now()

        memory_age = current_time - item.created_at

        ttl = timedelta(
            minutes=(
                self.config
                .working_memory_ttl_minutes
            )
        )

        ttl_seconds = ttl.total_seconds()

        if ttl_seconds <= 0:
            return 1.0

        age_ratio = (
            memory_age.total_seconds()
            / ttl_seconds
        )

        age_ratio = max(
            0.0,
            min(age_ratio, 1.0),
        )

        return 1.0 - age_ratio * 0.5