from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class MemoryItem:
    """
    表示 Agent 保存的一条记忆。

    例如：
    - 用户正在学习 Hello-Agents
    - 用户已经完成 Chapter 7
    - 用户偏好详细解释 Python 代码
    """

    # 记忆正文
    content: str

    # 记忆类型：
    # working：工作记忆
    # episodic：情景记忆
    # semantic：语义记忆
    memory_type: str = "working"

    # 记忆的重要程度，范围为 0.0～1.0
    importance: float = 0.5

    # 附加信息，例如用户 ID、来源和标签
    metadata: dict[str, Any] = field(default_factory=dict)

    # 每条记忆的唯一编号
    id: str = field(default_factory=lambda: uuid4().hex)

    # 记忆创建时间
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """
        MemoryItem 创建完成后，自动检查参数是否合法。
        """

        if not isinstance(self.content, str):
            raise TypeError("content 必须是字符串。")

        if not self.content.strip():
            raise ValueError("content 不能为空。")

        valid_memory_types = {
            "working",
            "episodic",
            "semantic",
        }

        if self.memory_type not in valid_memory_types:
            raise ValueError(
                "memory_type 必须是 working、episodic 或 semantic。"
            )

        if not isinstance(self.importance, (int, float)):
            raise TypeError("importance 必须是数字。")

        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("importance 必须在 0.0～1.0 之间。")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata 必须是字典。")

    def to_dict(self) -> dict[str, Any]:
        """
        将 MemoryItem 转换成普通字典。

        后续保存到 JSON 文件时会使用这个方法。
        """

        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(
                timespec="seconds"
            ),
        }


    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "MemoryItem":
        """
        根据字典重新创建 MemoryItem 对象。

        这个方法与 to_dict() 相反：

        MemoryItem
            ↓ to_dict()
        字典
            ↓ JSON 保存
        JSON 文件

        读取时：

        JSON 文件
            ↓ json.load()
        字典
            ↓ from_dict()
        MemoryItem
        """

        if not isinstance(data, dict):
            raise TypeError("data 必须是字典。")

        required_fields = {
            "id",
            "content",
            "memory_type",
            "importance",
            "created_at",
        }

        missing_fields = required_fields - data.keys()

        if missing_fields:
            raise ValueError(
                f"记忆数据缺少字段：{sorted(missing_fields)}"
            )

        created_at = data["created_at"]

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        if not isinstance(created_at, datetime):
            raise TypeError(
                "created_at 必须是 ISO 时间字符串或 datetime 对象。"
            )

        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=data["memory_type"],
            importance=data["importance"],
            metadata=data.get("metadata", {}),
            created_at=created_at,
        )


@dataclass
class MemoryConfig:
    """
    记忆系统的统一配置。

    后续创建 WorkingMemory、EpisodicMemory 和
    SemanticMemory 时，可以共享这些配置。
    """

    # 工作记忆最多保存多少条
    working_memory_capacity: int = 50

    # 工作记忆的有效时间，单位为分钟
    working_memory_ttl_minutes: int = 60

    # 长期记忆保存路径
    storage_path: str = "data/memories.json"

    # 默认返回多少条搜索结果
    default_search_limit: int = 5

    # 默认的重要性最低阈值
    min_importance: float = 0.0

    def __post_init__(self) -> None:
        """
        MemoryConfig 创建后自动检查配置是否合法。
        """

        if self.working_memory_capacity <= 0:
            raise ValueError(
                "working_memory_capacity 必须大于 0。"
            )

        if self.working_memory_ttl_minutes <= 0:
            raise ValueError(
                "working_memory_ttl_minutes 必须大于 0。"
            )

        if not isinstance(self.storage_path, str):
            raise TypeError("storage_path 必须是字符串。")

        if not self.storage_path.strip():
            raise ValueError("storage_path 不能为空。")

        if self.default_search_limit <= 0:
            raise ValueError(
                "default_search_limit 必须大于 0。"
            )

        if not 0.0 <= self.min_importance <= 1.0:
            raise ValueError(
                "min_importance 必须在 0.0～1.0 之间。"
            )


class BaseMemory(ABC):
    """
    所有记忆模块共同遵守的抽象基类。

    WorkingMemory、EpisodicMemory 和 SemanticMemory
    都需要继承这个类，并实现其中的抽象方法。
    """

    def __init__(self, config: MemoryConfig | None = None):
        """
        初始化记忆模块。

        config:
            记忆系统配置。

            如果调用者没有传入配置，
            就自动创建一份默认配置。
        """

        self.config = config or MemoryConfig()

    @abstractmethod
    def add(self, item: MemoryItem) -> str:
        """
        添加一条记忆。

        返回：
            新增记忆的 ID。
        """

        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int | None = None,
        min_importance: float | None = None,
    ) -> list[MemoryItem]:
        """
        搜索相关记忆。

        query:
            搜索关键词。

        limit:
            最多返回多少条结果。

        min_importance:
            只返回重要性不低于该值的记忆。
        """

        raise NotImplementedError

    @abstractmethod
    def remove(self, memory_id: str) -> bool:
        """
        根据记忆 ID 删除一条记忆。

        返回：
            删除成功返回 True；
            没找到记忆返回 False。
        """

        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[MemoryItem]:
        """
        返回当前记忆模块中的全部记忆。
        """

        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """
        清空当前记忆模块中的全部记忆。
        """

        raise NotImplementedError

    def __len__(self) -> int:
        """
        返回当前记忆数量。

        因为 BaseMemory 已经要求子类实现 get_all()，
        所以这里可以直接复用 get_all()。
        """

        return len(self.get_all())