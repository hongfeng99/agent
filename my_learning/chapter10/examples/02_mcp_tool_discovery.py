from hello_agents.tools import MCPTool


def main() -> None:
    """
    MCP 工具发现示例。

    学习目标：
    1. 连接 HelloAgents 内置 MCP Server；
    2. 查询服务器提供的工具；
    3. 调用其中的 add 工具；
    4. 理解 list_tools 和 call_tool 的区别。
    """

    print("=" * 60)
    print("创建 MCPTool")
    print("=" * 60)

    # 没有传入 server_command，
    # 因此使用 HelloAgents 内置的演示 MCP Server。
    mcp_tool = MCPTool()

    # --------------------------------------------------
    # 第一步：发现服务器提供了哪些工具
    # --------------------------------------------------

    print("\n[步骤 1] 查询 MCP Server 提供的工具")

    tools_result = mcp_tool.run(
        {
            "action": "list_tools",
        }
    )

    print("\n工具发现结果：")
    print(tools_result)

    # --------------------------------------------------
    # 第二步：调用其中的 add 工具
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("[步骤 2] 调用 add 工具")
    print("=" * 60)

    add_result = mcp_tool.run(
        {
            "action": "call_tool",
            "tool_name": "add",
            "arguments": {
                "a": 35,
                "b": 17,
            },
        }
    )

    print("\n工具调用结果：")
    print(add_result)

    print("\n" + "=" * 60)
    print("MCP 工具发现与调用测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()