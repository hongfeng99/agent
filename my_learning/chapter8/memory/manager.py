from dataclasses import replace
from .base import BaseMemory, MemoryItem

class MemoryManager:
    """
    记忆管理器。

    负责统一管理不同类型的记忆模块，例如：

    - WorkingMemory：工作记忆
    - EpisodicMemory：情景记忆
    - SemanticMemory：语义记忆

    MemoryManager 本身不直接保存记忆，
    而是根据 memory_type 将操作分发给对应的记忆模块。
    """

    VALID_MEMORY_TYPES = {
        "working",
        "episodic",
        "semantic",
    }

    def __init__(
        self,
        memories: dict[str, BaseMemory] | None = None,
    ) -> None:
        """
        初始化记忆管理器。

        memories:
            已经创建好的记忆模块。

            例如：

            {
                "working": WorkingMemory(),
                "episodic": EpisodicMemory(),
                "semantic": SemanticMemory(),
            }
        """

        self.memories: dict[str, BaseMemory] = {}

        if memories is not None:
            for memory_type, memory in memories.items():
                self.register(
                    memory_type=memory_type,
                    memory=memory,
                )

    def register(
        self,
        memory_type: str,
        memory: BaseMemory,
    ) -> None:
        """
        注册一个记忆模块。

        memory_type:
            记忆类型，例如 working、episodic、semantic。

        memory:
            真正负责保存和检索数据的记忆对象。
        """

        self._validate_memory_type(memory_type)

        if not isinstance(memory, BaseMemory):
            raise TypeError(
                "memory 必须是 BaseMemory 的子类实例。"
            )

        self.memories[memory_type] = memory

    def add(self, item: MemoryItem) -> str:
        """
        添加一条记忆。

        根据 item.memory_type，
        自动将记忆分发给对应的记忆模块。

        返回：
            被添加记忆的 ID。
        """

        if not isinstance(item, MemoryItem):
            raise TypeError("item 必须是 MemoryItem 对象。")

        memory = self._get_memory(item.memory_type)

        return memory.add(item)

    def update(
        self,
        memory_id: str,
        content: str | None = None,
        importance: float | None = None,
        metadata: dict | None = None,
    ) -> MemoryItem:
        """
        更新一条已有记忆。

        memory_id:
            需要更新的记忆 ID。

        content:
            新的记忆内容。
            如果为 None，就保持原内容。

        importance:
            新的重要性。
            如果为 None，就保持原重要性。

        metadata:
            需要补充或覆盖的元数据。
            新旧 metadata 会进行合并。

        返回：
            更新后的 MemoryItem。
        """

        if not isinstance(memory_id, str):
            raise TypeError("memory_id 必须是字符串。")

        memory_id = memory_id.strip()

        if not memory_id:
            raise ValueError("memory_id 不能为空。")

        if content is not None:
            if not isinstance(content, str):
                raise TypeError("content 必须是字符串。")

            content = content.strip()

            if not content:
                raise ValueError("content 不能为空。")

        if importance is not None:
            if not isinstance(importance, (int, float)):
                raise TypeError("importance 必须是数字。")

            if not 0 <= importance <= 1:
                raise ValueError(
                    "importance 必须位于 0 到 1 之间。"
                )

        if metadata is not None:
            if not isinstance(metadata, dict):
                raise TypeError("metadata 必须是字典。")

        # 依次在每个记忆模块中查找目标记忆
        for memory in self.memories.values():
            for old_item in memory.get_all():
                if old_item.id != memory_id:
                    continue

                changes = {}

                if content is not None:
                    changes["content"] = content

                if importance is not None:
                    changes["importance"] = float(importance)

                if metadata is not None:
                    changes["metadata"] = {
                        **old_item.metadata,
                        **metadata,
                    }

                # 根据旧记忆创建更新后的新对象
                updated_item = replace(
                    old_item,
                    **changes,
                )

                # 先删除旧版本
                removed = memory.remove(memory_id)

                if not removed:
                    raise RuntimeError(
                        f"无法删除旧记忆：{memory_id}"
                    )

                try:
                    # 再保存新版本
                    memory.add(updated_item)
                except Exception:
                    # 如果新版本保存失败，恢复旧版本
                    memory.add(old_item)
                    raise

                return updated_item

        raise KeyError(
            f"没有找到 ID 为 {memory_id} 的记忆。"
        )

    def forget(
        self,
        threshold: float,
        memory_types: list[str] | None = None,
    ) -> list[MemoryItem]:
        """
        遗忘重要性低于指定阈值的记忆。

        threshold:
            重要性阈值。

            例如 threshold=0.4，
            会删除 importance 小于 0.4 的记忆。

        memory_types:
            指定在哪些记忆模块中执行遗忘。

            例如：

            ["working", "episodic"]

            如果为 None，则检查全部已注册的记忆模块。

        返回：
            被删除的 MemoryItem 列表。
        """

        if not isinstance(threshold, (int, float)):
            raise TypeError("threshold 必须是数字。")

        if not 0 <= threshold <= 1:
            raise ValueError(
                "threshold 必须位于 0 到 1 之间。"
            )

        if memory_types is None:
            selected_types = list(self.memories.keys())
        else:
            if not isinstance(memory_types, list):
                raise TypeError(
                    "memory_types 必须是字符串列表。"
                )

            selected_types = memory_types

        forgotten_items: list[MemoryItem] = []

        for memory_type in selected_types:
            memory = self._get_memory(memory_type)

            # 使用 list() 创建副本，
            # 避免遍历过程中删除元素影响循环。
            items = list(memory.get_all())

            for item in items:
                if item.importance >= threshold:
                    continue

                removed = memory.remove(item.id)

                if removed:
                    forgotten_items.append(item)

        return forgotten_items


    def search(
        self,
        query: str,
        memory_types: list[str] | None = None,
        limit: int | None = 5,
        min_importance: float | None = None,
    ) -> list[MemoryItem]:
        """
        在一种或多种记忆中搜索。

        query:
            用户查询内容。

        memory_types:
            指定搜索哪些记忆类型。

            例如：

            ["episodic", "semantic"]

            如果没有传入，则搜索全部已注册的记忆模块。

        limit:
            最多返回多少条结果。

        min_importance:
            最低重要性阈值。
        """

        if not isinstance(query, str):
            raise TypeError("query 必须是字符串。")

        query = query.strip()

        if not query:
            raise ValueError("query 不能为空。")

        if limit is not None and limit <= 0:
            raise ValueError("limit 必须大于 0。")

        if memory_types is None:
            selected_types = list(self.memories.keys())
        else:
            selected_types = memory_types

        all_results: list[MemoryItem] = []
        seen_ids: set[str] = set()

        for memory_type in selected_types:
            memory = self._get_memory(memory_type)

            results = memory.search(
                query=query,
                limit=limit,
                min_importance=min_importance,
            )

            for item in results:
                # 避免相同 ID 的记忆重复出现
                if item.id in seen_ids:
                    continue

                seen_ids.add(item.id)
                all_results.append(item)

        # 当前第一版没有统一的相似度分数字段，
        # 因此先按照重要性从高到低排序。
        all_results.sort(
            key=lambda item: item.importance,
            reverse=True,
        )

        if limit is None:
            return all_results

        return all_results[:limit]

    def get_all(
        self,
        memory_type: str | None = None,
    ) -> list[MemoryItem]:
        """
        获取记忆。

        memory_type:
            如果指定类型，只获取该类型的记忆；
            如果不指定，则获取全部记忆。
        """

        if memory_type is not None:
            memory = self._get_memory(memory_type)
            return memory.get_all()

        all_items: list[MemoryItem] = []

        for memory in self.memories.values():
            all_items.extend(memory.get_all())

        # 按创建时间从新到旧排列
        all_items.sort(
            key=lambda item: item.created_at,
            reverse=True,
        )

        return all_items



    def consolidate(
        self,
        source_type: str = "working",
        target_type: str = "episodic",
        min_importance: float = 0.7,
        limit: int | None = None,
        remove_from_source: bool = True,
    ) -> list[MemoryItem]:
        """
        将重要记忆从一个记忆模块整合到另一个模块。

        默认行为：

        WorkingMemory
            ↓
        EpisodicMemory

        source_type:
            来源记忆类型。

        target_type:
            目标记忆类型。

        min_importance:
            只有 importance 大于或等于该值的记忆，
            才会被整合。

        limit:
            最多整合多少条记忆。
            如果为 None，则不限制数量。

        remove_from_source:
            整合成功后，是否从来源记忆中删除旧记忆。

            True：
                相当于“移动”。

            False：
                相当于“复制”。

        返回：
            被整合后的 MemoryItem 列表。
        """

        if source_type == target_type:
            raise ValueError(
                "source_type 和 target_type 不能相同。"
            )

        if not isinstance(min_importance, (int, float)):
            raise TypeError(
                "min_importance 必须是数字。"
            )

        if not 0 <= min_importance <= 1:
            raise ValueError(
                "min_importance 必须位于 0 到 1 之间。"
            )

        if limit is not None:
            if not isinstance(limit, int):
                raise TypeError("limit 必须是整数。")

            if limit <= 0:
                raise ValueError("limit 必须大于 0。")

        if not isinstance(remove_from_source, bool):
            raise TypeError(
                "remove_from_source 必须是布尔值。"
            )

        source_memory = self._get_memory(source_type)
        target_memory = self._get_memory(target_type)

        # 找出重要性达到阈值的记忆
        candidates = [
            item
            for item in source_memory.get_all()
            if item.importance >= min_importance
        ]

        # 重要性从高到低排序
        candidates.sort(
            key=lambda item: item.importance,
            reverse=True,
        )

        if limit is not None:
            candidates = candidates[:limit]

        consolidated_items: list[MemoryItem] = []

        for old_item in candidates:
            # 给元数据增加整合来源信息
            new_metadata = {
                **old_item.metadata,
                "consolidated_from": source_type,
            }

            # 创建目标记忆类型的新对象
            consolidated_item = replace(
                old_item,
                memory_type=target_type,
                metadata=new_metadata,
            )

            # 先写入目标记忆。
            # 如果这里失败，来源记忆不会被删除。
            target_memory.add(consolidated_item)

            if remove_from_source:
                removed = source_memory.remove(old_item.id)

                if not removed:
                    # 来源删除失败时，回滚目标记忆
                    target_memory.remove(
                        consolidated_item.id
                    )

                    raise RuntimeError(
                        f"无法从 {source_type} 中删除"
                        f"记忆 {old_item.id}。"
                    )

            consolidated_items.append(
                consolidated_item
            )

        return consolidated_items
    

    def get(
        self,
        memory_id: str,
        memory_type: str | None = None,
    ) -> MemoryItem | None:
        """
        根据 ID 查找一条记忆。

        memory_type:
            如果指定记忆类型，只在该类型中查找；
            如果不指定，则搜索所有已注册的记忆模块。

        返回：
            找到时返回 MemoryItem；
            没找到时返回 None。
        """

        if not isinstance(memory_id, str):
            raise TypeError("memory_id 必须是字符串。")

        memory_id = memory_id.strip()

        if not memory_id:
            raise ValueError("memory_id 不能为空。")

        if memory_type is not None:
            memory = self._get_memory(memory_type)

            for item in memory.get_all():
                if item.id == memory_id:
                    return item

            return None

        for memory in self.memories.values():
            for item in memory.get_all():
                if item.id == memory_id:
                    return item

        return None

    def remove(
        self,
        memory_id: str,
        memory_type: str | None = None,
    ) -> bool:
        """
        删除一条记忆。

        memory_type:
            如果知道记忆属于哪种类型，可以直接指定；
            如果不指定，则依次在所有记忆模块中查找。
        """

        if not isinstance(memory_id, str):
            raise TypeError("memory_id 必须是字符串。")

        memory_id = memory_id.strip()

        if not memory_id:
            raise ValueError("memory_id 不能为空。")

        if memory_type is not None:
            memory = self._get_memory(memory_type)
            return memory.remove(memory_id)

        for memory in self.memories.values():
            removed = memory.remove(memory_id)

            if removed:
                return True

        return False

    def clear(
        self,
        memory_type: str | None = None,
    ) -> int:
        """
        清空记忆。

        返回：
            被清除的记忆数量。
        """

        if memory_type is not None:
            memory = self._get_memory(memory_type)

            count = len(memory.get_all())
            memory.clear()

            return count

        total_count = 0

        for memory in self.memories.values():
            total_count += len(memory.get_all())
            memory.clear()

        return total_count

    def stats(self) -> dict[str, int]:
        """
        返回每种记忆的数量统计。
        """

        return {
            memory_type: len(memory.get_all())
            for memory_type, memory in self.memories.items()
        }

    def _get_memory(
        self,
        memory_type: str,
    ) -> BaseMemory:
        """
        根据 memory_type 获取对应记忆模块。
        """

        self._validate_memory_type(memory_type)

        if memory_type not in self.memories:
            raise KeyError(
                f"记忆模块 {memory_type} 尚未注册。"
            )

        return self.memories[memory_type]

    @classmethod
    def _validate_memory_type(
        cls,
        memory_type: str,
    ) -> None:
        """
        验证记忆类型是否合法。
        """

        if not isinstance(memory_type, str):
            raise TypeError("memory_type 必须是字符串。")

        if memory_type not in cls.VALID_MEMORY_TYPES:
            raise ValueError(
                "memory_type 必须是 "
                "working、episodic 或 semantic。"
            )