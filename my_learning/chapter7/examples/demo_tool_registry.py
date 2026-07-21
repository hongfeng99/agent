from typing import Any, Dict

from hello_agents.tools.base import Tool
from hello_agents.tools.registry import ToolRegistry


class EchoTool(Tool):
    """
    测试工具。

    功能：把传入的文本原样返回。
    """

    def __init__(self) -> None:
        super().__init__(
            name="echo",
            description="返回用户传入的文本。",
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        text = parameters.get("text")

        if text is None:
            raise ValueError("缺少参数：text")

        return f"EchoTool 返回：{text}"


def main() -> None:
    registry = ToolRegistry()

    echo_tool = EchoTool()

    # 注册工具
    registry.register(echo_tool)

    print("工具数量：")
    print(len(registry))

    print("\n是否存在 echo 工具：")
    print("echo" in registry)

    print("\n工具说明：")
    print(registry.get_tools_description())

    print("\n执行 echo 工具：")

    result = registry.execute(
        name="echo",
        parameters={
            "text": "Hello Chapter 7",
        },
    )

    print(result)

    print("\n执行不存在的工具：")

    missing_result = registry.execute(
        name="unknown",
        parameters={},
    )

    print(missing_result)

    print("\n执行缺少参数的工具：")

    error_result = registry.execute(
        name="echo",
        parameters={},
    )

    print(error_result)


if __name__ == "__main__":
    main()