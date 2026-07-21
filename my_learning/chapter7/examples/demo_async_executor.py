import asyncio
import time
from typing import Any, Dict

from hello_agents import (
    AsyncToolExecutor,
    Tool,
    ToolCall,
    ToolRegistry,
)


class DelayTool(Tool):
    """
    用于测试异步执行的等待工具。

    它会等待指定秒数，然后返回结果。
    """

    def __init__(self) -> None:
        super().__init__(
            name="delay",
            description=(
                "等待指定秒数后返回结果。"
                "仅用于测试异步并发。"
            ),
        )

    def run(
        self,
        parameters: Dict[str, Any],
    ) -> str:
        seconds = parameters.get("seconds")
        label = parameters.get(
            "label",
            "未命名任务",
        )

        if not isinstance(seconds, (int, float)):
            raise TypeError(
                "seconds 必须是数字。"
            )

        if seconds < 0:
            raise ValueError(
                "seconds 不能小于 0。"
            )

        time.sleep(seconds)

        return (
            f"{label} 已完成，"
            f"等待时间为 {seconds} 秒。"
        )


async def main() -> None:
    registry = ToolRegistry()

    registry.register(
        DelayTool()
    )

    executor = AsyncToolExecutor(
        tool_registry=registry,
        max_concurrency=3,
    )

    tool_calls = [
        ToolCall(
            tool_name="delay",
            parameters={
                "seconds": 2,
                "label": "任务A",
            },
            call_id="call_a",
        ),
        ToolCall(
            tool_name="delay",
            parameters={
                "seconds": 3,
                "label": "任务B",
            },
            call_id="call_b",
        ),
        ToolCall(
            tool_name="delay",
            parameters={
                "seconds": 1,
                "label": "任务C",
            },
            call_id="call_c",
        ),
    ]

    start_time = time.perf_counter()

    results = await executor.execute_tools_parallel(
        tool_calls
    )

    elapsed_time = (
        time.perf_counter() - start_time
    )

    print("执行结果：")

    for result in results:
        print(
            f"\n调用编号：{result['call_id']}"
        )
        print(
            f"工具名称：{result['tool_name']}"
        )
        print(
            f"执行成功：{result['success']}"
        )
        print(
            f"执行结果：{result['result']}"
        )

    print(
        f"\n总执行时间：{elapsed_time:.2f} 秒"
    )





if __name__ == "__main__":
    asyncio.run(main())