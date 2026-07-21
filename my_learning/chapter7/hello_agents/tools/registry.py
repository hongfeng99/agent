from typing import Any, Dict, List, Optional

from .base import Tool


from ..exceptions import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistrationError,
)

class ToolRegistry:
    """
    工具注册表。

    负责：

    1. 注册工具；
    2. 根据名称查找工具；
    3. 执行工具；
    4. 删除工具；
    5. 返回所有工具的说明。
    """

    def __init__(self) -> None:
        # 工具名称 -> Tool 对象
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        注册工具。
        """

        if not isinstance(tool, Tool):
            raise TypeError(
                "注册对象必须是 Tool 的子类实例。"
            )

        if tool.name in self._tools:
            raise ToolRegistrationError(
                f"工具已经存在：{tool.name}"
            )

        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """
        删除指定工具。
        """

        if name not in self._tools:
            raise ToolNotFoundError(
                f"工具不存在：{name}"
            )

        del self._tools[name]

    def get(self, name: str) -> Optional[Tool]:
        """
        根据名称获取工具。

        找不到时返回 None。
        """

        return self._tools.get(name)

    def execute(
        self,
        name: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        执行工具并始终返回字符串。

        工具执行失败时，将异常转换为错误文本。
        适合 ReActAgent，因为错误文本可以作为
        Observation 再次提供给大模型。
        """

        try:
            return self.execute_or_raise(
                name=name,
                parameters=parameters,
            )

        except (
            ToolNotFoundError,
            ToolExecutionError,
        ) as error:
            return str(error)

    def list_tools(self) -> List[Tool]:
        """
        返回所有已经注册的工具。
        """

        return list(self._tools.values())

    def get_tools_description(self) -> List[Dict[str, str]]:
        """
        返回所有工具的名称和描述。

        后续会把这个结果加入 ReAct 提示词。
        """

        return [
            tool.get_description()
            for tool in self._tools.values()
        ]

    def __len__(self) -> int:
        """
        返回已注册工具数量。
        """

        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """
        支持使用：

        "calculator" in registry
        """

        return name in self._tools
    
    
    def format_tools_description(self) -> str:
        """
        将所有工具格式化成适合放入提示词的字符串。
        """

        if not self._tools:
            return "暂无可用工具"

        descriptions = []

        for tool in self._tools.values():
            descriptions.append(
                f"- {tool.name}: {tool.description}"
            )

        return "\n".join(descriptions)
    

    def execute_or_raise(
        self,
        name: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        执行工具。

        与 execute() 不同：
        执行失败时会抛出自定义异常，
        适合工具链等需要严格控制错误的场景。
        """

        tool = self.get(name)

        if tool is None:
            raise ToolNotFoundError(
                f"工具不存在：{name}"
            )

        try:
            return tool.run(parameters)

        except ToolExecutionError:
            # 已经是框架工具异常时，直接继续抛出。
            raise

        except Exception as error:
            raise ToolExecutionError(
                f"工具 {name} 执行失败："
                f"{type(error).__name__}: {error}"
            ) from error