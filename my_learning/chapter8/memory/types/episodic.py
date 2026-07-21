from datetime import datetime
from pathlib import Path

from ..base import BaseMemory, MemoryConfig, MemoryItem
from ..embedding import BaseEmbedding, create_embedding_model
from ..storage.json_store import JsonMemoryStorage


class EpisodicMemory(BaseMemory):
    """
    Agent 的情景记忆。

    情景记忆用于保存具体发生过的事件，例如：

    - 用户完成了 Chapter 7；
    - 用户运行程序时遇到报错；
    - 用户在某次会话中选择了某种方案。

    当前版本使用：

    - JSON：持久化保存记忆；
    - TF-IDF：计算文本相似度；
    - metadata：保存事件类型、会话 ID 等信息。
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        storage_path: str | None = None,
        embedding_model: BaseEmbedding | None = None,
    ) -> None:
        """
        初始化情景记忆。

        config:
            记忆系统配置。

        storage_path:
            情景记忆 JSON 文件路径。

        embedding_model:
            文本嵌入模型。

            如果没有传入，默认使用 TF-IDF。
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
        添加一条情景记忆。

        相同会话中，如果存在内容完全相同的记忆，
        就合并重要性和 metadata，而不是重复保存。
        """

        if not isinstance(item, MemoryItem):
            raise TypeError("item 必须是 MemoryItem 对象。")

        item.memory_type = "episodic"

        duplicated_item = self._find_duplicate(
            item=item,
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
        event_type: str | None = None,
        session_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[MemoryItem]:
        """
        搜索相关的情景记忆。

        query:
            查询文本。

        limit:
            最多返回多少条结果。

        min_importance:
            只搜索重要性不低于该值的记忆。

        event_type:
            只搜索指定事件类型，例如 learning_progress。

        session_id:
            只搜索指定会话中的事件。

        start_time:
            只搜索该时间之后创建的事件。

        end_time:
            只搜索该时间之前创建的事件。
        """

        self._validate_search_arguments(
            query=query,
            limit=limit,
            min_importance=min_importance,
            start_time=start_time,
            end_time=end_time,
        )

        if limit is None:
            limit = self.config.default_search_limit

        if min_importance is None:
            min_importance = self.config.min_importance

        candidate_items = []

        for item in self.storage.load():
            if item.importance < min_importance:
                continue

            if not self._matches_filters(
                item=item,
                event_type=event_type,
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
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

            recency_score = (
                self._calculate_recency_score(item)
            )

            final_score = (
                vector_score * 0.65
                + keyword_score * 0.15
                + item.importance * 0.15
                + recency_score * 0.05
            )

            # 文本完全无关时，不应只靠重要性进入结果。
            text_relevance = (
                vector_score * 0.8
                + keyword_score * 0.2
            )

            if text_relevance <= 0:
                continue

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
        根据 ID 删除一条情景记忆。
        """

        return self.storage.remove(memory_id)

    def get_all(self) -> list[MemoryItem]:
        """
        返回全部情景记忆。
        """

        return self.storage.load()

    def clear(self) -> None:
        """
        清空全部情景记忆。
        """

        self.storage.clear()

    def get(
        self,
        memory_id: str,
    ) -> MemoryItem | None:
        """
        根据 ID 获取一条情景记忆。
        """

        return self.storage.get(memory_id)

    def update(
        self,
        item: MemoryItem,
    ) -> bool:
        """
        更新一条情景记忆。
        """

        if not isinstance(item, MemoryItem):
            raise TypeError(
                "item 必须是 MemoryItem。"
            )

        item.memory_type = "episodic"

        return self.storage.update(item)

    def _find_duplicate(
        self,
        item: MemoryItem,
    ) -> MemoryItem | None:
        """
        查找同一会话中内容完全相同的记忆。

        不同 session_id 中内容相同的事件，
        仍然可以被保存为不同情景记忆。
        """

        normalized_content = (
            item.content.strip().lower()
        )

        new_session_id = item.metadata.get(
            "session_id"
        )

        for existing_item in self.storage.load():
            existing_content = (
                existing_item.content
                .strip()
                .lower()
            )

            existing_session_id = (
                existing_item.metadata.get(
                    "session_id"
                )
            )

            content_matched = (
                existing_content
                == normalized_content
            )

            session_matched = (
                existing_session_id
                == new_session_id
            )

            if content_matched and session_matched:
                return existing_item

        return None

    @staticmethod
    def _matches_filters(
        item: MemoryItem,
        event_type: str | None,
        session_id: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> bool:
        """
        检查一条记忆是否满足过滤条件。
        """

        if event_type is not None:
            item_event_type = item.metadata.get(
                "event_type"
            )

            if item_event_type != event_type:
                return False

        if session_id is not None:
            item_session_id = item.metadata.get(
                "session_id"
            )

            if item_session_id != session_id:
                return False

        if (
            start_time is not None
            and item.created_at < start_time
        ):
            return False

        if (
            end_time is not None
            and item.created_at > end_time
        ):
            return False

        return True

    @staticmethod
    def _split_words(
        text: str,
    ) -> set[str]:
        """
        将查询文本转换成关键词集合。

        英文主要按照空格分割；
        中文同时保留完整查询内容。
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
    def _calculate_recency_score(
        item: MemoryItem,
    ) -> float:
        """
        根据记忆创建时间计算新旧程度。

        刚创建的事件接近 1.0；
        30 天前的事件约为 0.5；
        时间越久，分数越低。
        """

        age = datetime.now() - item.created_at

        age_days = max(
            0.0,
            age.total_seconds() / 86400,
        )

        return 1.0 / (
            1.0 + age_days / 30.0
        )

    @staticmethod
    def _validate_search_arguments(
        query: str,
        limit: int | None,
        min_importance: float | None,
        start_time: datetime | None,
        end_time: datetime | None,
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

        if (
            start_time is not None
            and not isinstance(
                start_time,
                datetime,
            )
        ):
            raise TypeError(
                "start_time 必须是 datetime。"
            )

        if (
            end_time is not None
            and not isinstance(
                end_time,
                datetime,
            )
        ):
            raise TypeError(
                "end_time 必须是 datetime。"
            )

        if (
            start_time is not None
            and end_time is not None
            and start_time > end_time
        ):
            raise ValueError(
                "start_time 不能晚于 end_time。"
            )

    def _build_storage_path(self) -> str:
        """
        根据 config.storage_path 所在目录，
        生成 episodic_memories.json。
        """

        base_path = Path(
            self.config.storage_path
        )

        episodic_path = (
            base_path.parent
            / "episodic_memories.json"
        )

        return str(episodic_path)