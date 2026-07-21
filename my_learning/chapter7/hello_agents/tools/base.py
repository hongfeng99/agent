from abc import ABC, abstractmethod
from typing import Any, Dict


class Tool(ABC):
    """
    所有工具的抽象基类。

    每个具体工具都必须具有：

    1. name：工具名称；
    2. description：工具说明；
    3. run()：真正执行工具的方法。
    """

    def __init__(
        self,
        name: str,
        description: str,
    ) -> None:
        if not name.strip():
            raise ValueError("工具名称不能为空。")

        if not description.strip():
            raise ValueError("工具描述不能为空。")

        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行工具。

        parameters:
            工具执行时需要的参数。

        返回：
            工具执行结果的字符串形式。
        """

        raise NotImplementedError

    def get_description(self) -> Dict[str, str]:
        """
        返回工具的基础说明。

        后续可以把这些说明提供给大模型，
        让模型知道有哪些工具可以使用。
        """

        return {
            "name": self.name,
            "description": self.description,
        }