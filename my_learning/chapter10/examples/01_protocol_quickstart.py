from hello_agents.tools import MCPTool


def main() -> None:
    """
    Chapter 10 第一个 MCP 示例。

    使用 HelloAgents 内置的 MCP Server，
    调用其中的 add 工具完成加法计算。
    """

    # 创建 MCPTool。
    #
    # 这里没有传入外部服务器命令，
    # 因此使用 HelloAgents 提供的内置 MCP 服务。
    mcp_tool = MCPTool()

    # 通过统一的 run 方法向 MCP 服务发送请求。
    result = mcp_tool.run(
        {
            # call_tool 表示调用 MCP Server 提供的工具
            "action": "call_tool",

            # 要调用的具体工具名称
            "tool_name": "add",

            # 传给 add 工具的参数
            "arguments": {
                "a": 33,
                "b": 66,
            },
        }
    )

    print("=" * 60)
    print("MCP 调用结果")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()