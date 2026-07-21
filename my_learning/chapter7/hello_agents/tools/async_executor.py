import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .registry import ToolRegistry


@dataclass
class ToolCall:
    """
    表示一次待执行的工具调用。

    tool_name:
        要调用的工具名称。

    parameters:
        传递给工具的参数字典。

    call_id:
        可选的调用编号，用于区分不同任务。
    """

    tool_name: str
    parameters: Dict[str, Any]
    call_id: Optional[str] = None


class AsyncToolExecutor:
    """
    异步工具执行器。

    负责：
    1. 异步执行单个同步工具；
    2. 并发执行多个独立工具；
    3. 限制同时执行的工具数量；
    4. 收集每个工具的执行结果。
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        max_concurrency: int = 5,
    ) -> None:
        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError(
                "tool_registry 必须是 ToolRegistry 对象。"
            )

        if not isinstance(max_concurrency, int):
            raise TypeError(
                "max_concurrency 必须是整数。"
            )

        if max_concurrency <= 0:
            raise ValueError(
                "max_concurrency 必须大于 0。"
            )

        self.tool_registry = tool_registry
        self.max_concurrency = max_concurrency

        # 信号量用于限制同时运行的工具数量。
        self._semaphore = asyncio.Semaphore(
            max_concurrency
        )

    async def execute_tool_async(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        异步执行单个工具。

        ToolRegistry.execute() 本来是同步函数，
        这里使用 asyncio.to_thread()，
        将同步工具放到额外线程中运行。
        """

        if not isinstance(tool_name, str):
            raise TypeError(
                "tool_name 必须是字符串。"
            )

        tool_name = tool_name.strip()

        if not tool_name:
            raise ValueError(
                "tool_name 不能为空。"
            )

        if not isinstance(parameters, dict):
            raise TypeError(
                "parameters 必须是字典。"
            )

        async with self._semaphore:
            result = await asyncio.to_thread(
                self.tool_registry.execute,
                tool_name,
                parameters,
            )

        return result

    async def _execute_call(
        self,
        tool_call: ToolCall,
        position: int,
    ) -> Dict[str, Any]:
        """
        执行一个 ToolCall，并返回结构化结果。
        """

        try:
            result = await self.execute_tool_async(
                tool_name=tool_call.tool_name,
                parameters=tool_call.parameters,
            )

            failed = (
                result.startswith("工具不存在：")
                or result.startswith(
                    f"工具 {tool_call.tool_name} 执行失败："
                )
            )

            return {
                "position": position,
                "call_id": tool_call.call_id,
                "tool_name": tool_call.tool_name,
                "parameters": tool_call.parameters,
                "success": not failed,
                "result": result,
            }

        except Exception as error:
            return {
                "position": position,
                "call_id": tool_call.call_id,
                "tool_name": tool_call.tool_name,
                "parameters": tool_call.parameters,
                "success": False,
                "result": (
                    f"{type(error).__name__}: {error}"
                ),
            }

    async def execute_tools_parallel(
        self,
        tool_calls: List[ToolCall],
    ) -> List[Dict[str, Any]]:
        """
        并发执行多个互不依赖的工具调用。

        返回结果的顺序与 tool_calls 中的顺序一致。
        """

        if not isinstance(tool_calls, list):
            raise TypeError(
                "tool_calls 必须是列表。"
            )

        if not tool_calls:
            return []

        for index, tool_call in enumerate(
            tool_calls,
            start=1,
        ):
            if not isinstance(tool_call, ToolCall):
                raise TypeError(
                    f"第 {index} 个任务不是 ToolCall 对象。"
                )

        tasks = [
            self._execute_call(
                tool_call=tool_call,
                position=index,
            )
            for index, tool_call in enumerate(
                tool_calls,
                start=1,
            )
        ]

        results = await asyncio.gather(*tasks)

        return results    