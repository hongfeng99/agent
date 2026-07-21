import json
from json import JSONDecodeError
from pathlib import Path

from ..base import MemoryItem

class JsonMemoryStorage:
    """
    使用 JSON 文件持久化保存记忆。

    主要负责：

    1. 创建存储文件；
    2. 将 MemoryItem 列表保存到 JSON；
    3. 从 JSON 文件恢复 MemoryItem；
    4. 添加、删除和清空记忆。
    """

    def __init__(
        self,
        storage_path: str | Path,
    ) -> None:
        """
        初始化 JSON 存储。

        storage_path:
            JSON 文件保存位置，例如：

            data/episodic_memories.json
        """

        self.storage_path = Path(storage_path)

        self._ensure_storage_file()

    def _ensure_storage_file(self) -> None:
        """
        确保存储目录和 JSON 文件存在。

        如果目录不存在，就自动创建目录。

        如果 JSON 文件不存在，就创建一个内容为 [] 的文件。
        """

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.storage_path.exists():
            self.storage_path.write_text(
                "[]",
                encoding="utf-8",
            )

    def load(self) -> list[MemoryItem]:
        """
        从 JSON 文件中读取全部记忆。

        返回：
            MemoryItem 对象列表。
        """

        try:
            text = self.storage_path.read_text(
                encoding="utf-8"
            )

            raw_data = json.loads(text)

        except JSONDecodeError as error:
            raise ValueError(
                f"JSON 文件格式错误：{self.storage_path}"
            ) from error

        if not isinstance(raw_data, list):
            raise ValueError(
                "记忆 JSON 文件的最外层必须是列表。"
            )

        memories: list[MemoryItem] = []

        for index, item_data in enumerate(raw_data):
            try:
                memory = MemoryItem.from_dict(item_data)

            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"第 {index + 1} 条记忆数据格式错误："
                    f"{error}"
                ) from error

            memories.append(memory)

        return memories

    def save(
        self,
        memories: list[MemoryItem],
    ) -> None:
        """
        将全部记忆写入 JSON 文件。

        注意：
            这里是覆盖写入，不是追加写入。
        """

        if not isinstance(memories, list):
            raise TypeError("memories 必须是列表。")

        data = []

        for item in memories:
            if not isinstance(item, MemoryItem):
                raise TypeError(
                    "memories 中的元素必须是 MemoryItem。"
                )

            data.append(item.to_dict())

        json_text = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

        self.storage_path.write_text(
            json_text,
            encoding="utf-8",
        )

    def add(
        self,
        item: MemoryItem,
    ) -> str:
        """
        添加一条记忆并立即保存。

        返回：
            新增记忆的 ID。
        """

        if not isinstance(item, MemoryItem):
            raise TypeError("item 必须是 MemoryItem。")

        memories = self.load()

        duplicated_memory = self._find_by_id(
            memories=memories,
            memory_id=item.id,
        )

        if duplicated_memory is not None:
            raise ValueError(
                f"记忆 ID 已存在：{item.id}"
            )

        memories.append(item)

        self.save(memories)

        return item.id

    def remove(
        self,
        memory_id: str,
    ) -> bool:
        """
        根据 ID 删除一条记忆。

        返回：
            找到并删除返回 True；
            没有找到返回 False。
        """

        if not isinstance(memory_id, str):
            raise TypeError("memory_id 必须是字符串。")

        if not memory_id.strip():
            raise ValueError("memory_id 不能为空。")

        memories = self.load()

        remaining_memories = [
            item
            for item in memories
            if item.id != memory_id
        ]

        if len(remaining_memories) == len(memories):
            return False

        self.save(remaining_memories)

        return True

    def get(
        self,
        memory_id: str,
    ) -> MemoryItem | None:
        """
        根据 ID 获取一条记忆。

        没有找到时返回 None。
        """

        if not isinstance(memory_id, str):
            raise TypeError("memory_id 必须是字符串。")

        memories = self.load()

        return self._find_by_id(
            memories=memories,
            memory_id=memory_id,
        )

    def update(
        self,
        updated_item: MemoryItem,
    ) -> bool:
        """
        根据 ID 更新一条已有记忆。

        返回：
            更新成功返回 True；
            没有找到目标记忆返回 False。
        """

        if not isinstance(updated_item, MemoryItem):
            raise TypeError(
                "updated_item 必须是 MemoryItem。"
            )

        memories = self.load()

        for index, item in enumerate(memories):
            if item.id == updated_item.id:
                memories[index] = updated_item
                self.save(memories)
                return True

        return False

    def clear(self) -> None:
        """
        清空 JSON 文件中的全部记忆。
        """

        self.save([])

    def count(self) -> int:
        """
        返回当前保存的记忆数量。
        """

        return len(self.load())

    @staticmethod
    def _find_by_id(
        memories: list[MemoryItem],
        memory_id: str,
    ) -> MemoryItem | None:
        """
        在记忆列表中根据 ID 查找记忆。
        """

        for item in memories:
            if item.id == memory_id:
                return item

        return None