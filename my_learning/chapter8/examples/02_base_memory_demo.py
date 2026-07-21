from memory.base import BaseMemory, MemoryConfig, MemoryItem


class DemoMemory(BaseMemory):
    """
    一个仅用于测试 BaseMemory 的简单记忆类。

    暂时使用 Python 列表保存数据。
    后面正式实现 WorkingMemory 时会替换它。
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
    ):
        super().__init__(config)

        self.memories: list[MemoryItem] = []

    def add(self, item: MemoryItem) -> str:
        """
        添加一条记忆，并返回记忆 ID。
        """

        self.memories.append(item)
        return item.id

    def search(
        self,
        query: str,
        limit: int | None = None,
        min_importance: float | None = None,
    ) -> list[MemoryItem]:
        """
        使用最简单的关键词方式搜索记忆。
        """

        if limit is None:
            limit = self.config.default_search_limit

        if min_importance is None:
            min_importance = self.config.min_importance

        results = []

        for item in self.memories:
            content_matched = (
                query.lower() in item.content.lower()
            )

            importance_matched = (
                item.importance >= min_importance
            )

            if content_matched and importance_matched:
                results.append(item)

        return results[:limit]

    def remove(self, memory_id: str) -> bool:
        """
        根据 ID 删除记忆。
        """

        for index, item in enumerate(self.memories):
            if item.id == memory_id:
                self.memories.pop(index)
                return True

        return False

    def get_all(self) -> list[MemoryItem]:
        """
        返回全部记忆的副本。
        """

        return self.memories.copy()

    def clear(self) -> None:
        """
        清空全部记忆。
        """

        self.memories.clear()


def main() -> None:
    config = MemoryConfig(
        working_memory_capacity=10,
        default_search_limit=3,
        min_importance=0.3,
    )

    memory = DemoMemory(config=config)

    first_memory = MemoryItem(
        content="用户正在学习 Hello-Agents Chapter 8。",
        memory_type="working",
        importance=0.9,
    )

    second_memory = MemoryItem(
        content="用户已经完成 Hello-Agents Chapter 7。",
        memory_type="episodic",
        importance=0.8,
    )

    third_memory = MemoryItem(
        content="用户今天喝了一杯水。",
        memory_type="working",
        importance=0.1,
    )

    first_id = memory.add(first_memory)
    second_id = memory.add(second_memory)
    memory.add(third_memory)

    print("第一条记忆 ID：", first_id)
    print("第二条记忆 ID：", second_id)

    print("\n当前记忆数量：", len(memory))

    print("\n搜索 Hello-Agents：")

    results = memory.search("Hello-Agents")

    for item in results:
        print(
            f"- {item.content} "
            f"重要性：{item.importance}"
        )

    print("\n删除第一条记忆：")

    removed = memory.remove(first_id)

    print("是否删除成功：", removed)
    print("删除后的数量：", len(memory))

    print("\n当前全部记忆：")

    for item in memory.get_all():
        print("-", item.content)

    print("\n清空全部记忆：")

    memory.clear()

    print("清空后的数量：", len(memory))


if __name__ == "__main__":
    main()