from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class Message:
    """
    Agent 框架内部统一使用的消息对象。

    role:
        消息角色，例如 system、user、assistant、tool。

    content:
        消息的文本内容。

    timestamp:
        消息创建时间。

    metadata:
        消息附加信息，例如工具名称、步骤编号等。
    """

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        """
        将 Message 转换成大模型 API 可以接收的字典格式。
        """

        return {
            "role": self.role,
            "content": self.content,
        }