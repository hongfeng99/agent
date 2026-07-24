import asyncio
from pathlib import Path
from typing import Any

from hello_agents.protocols import MCPClient


def format_result(result: Any, max_length: int = 2000) -> str:
    """
    将 MCP 返回结果转换成便于打印的字符串。

    max_length:
        限制打印长度，避免 README 内容过长。
    """

    text = str(result)

    if len(text) <= max_length:
        return text

    return text[:max_length] + "\n\n……内容过长，后续已省略……"


async def main() -> None:
    """
    使用 Stdio Transport 连接文件系统 MCP Server。

    完成三个操作：
    1. 发现服务器提供的工具；
    2. 查看项目根目录；
    3. 读取项目 README.md。
    """

    # 当前程序应当从项目根目录运行。
    project_root = Path.cwd().resolve()
    readme_path = project_root / "README.md"

    print("=" * 70)
    print("文件系统 MCP Client")
    print("=" * 70)
    print(f"允许访问的目录：{project_root}")

    # 在连接服务器前，先确认目标文件存在。
    if not readme_path.exists():
        raise FileNotFoundError(
            f"没有找到 README.md：{readme_path}\n"
            "请确认程序是在 hello-agents 项目根目录运行。"
        )

    # Windows 下 npx 实际对应 npx.cmd。
    #
    # 大多数环境直接写 npx 也可以；
    # 使用 npx.cmd 对 Windows 更明确。
    server_command = [
        "npx.cmd",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        str(project_root),
    ]

    # MCPClient 会根据命令启动一个外部 MCP Server 进程，
    # 并通过标准输入/标准输出与其通信。
    client = MCPClient(server_command)

    try:
        # async with 负责：
        # 1. 启动服务器；
        # 2. 建立连接；
        # 3. 退出时关闭连接和子进程。
        async with client:
            # -------------------------------------------------
            # 第一步：发现工具
            # -------------------------------------------------
            print("\n[步骤 1] 查询服务器工具")

            tools = await client.list_tools()

            tool_names: list[str] = []

            for index, tool in enumerate(tools, start=1):
                name = tool.get("name", "未知工具")
                description = tool.get("description", "无描述")

                tool_names.append(name)

                print(f"\n{index}. {name}")
                print(f"   描述：{description}")

            print("\n发现的工具名称：")
            print(tool_names)

            # -------------------------------------------------
            # 第二步：列出项目根目录
            # -------------------------------------------------
            print("\n" + "=" * 70)
            print("[步骤 2] 查看项目根目录")
            print("=" * 70)

            if "list_directory" in tool_names:
                directory_result = await client.call_tool(
                    "list_directory",
                    {
                        "path": str(project_root),
                    },
                )

                print(format_result(directory_result))
            else:
                print("当前服务器没有提供 list_directory 工具。")

            # -------------------------------------------------
            # 第三步：确定实际文件读取工具名
            # -------------------------------------------------
            #
            # 不同版本可能使用：
            # read_text_file
            # 或 read_file
            #
            # 所以先根据工具发现结果动态选择。
            if "read_text_file" in tool_names:
                read_tool_name = "read_text_file"
            elif "read_file" in tool_names:
                read_tool_name = "read_file"
            else:
                raise RuntimeError(
                    "服务器没有提供 read_text_file 或 read_file 工具。"
                )

            # -------------------------------------------------
            # 第四步：读取 README.md
            # -------------------------------------------------
            print("\n" + "=" * 70)
            print(f"[步骤 3] 使用 {read_tool_name} 读取 README.md")
            print("=" * 70)

            read_result = await client.call_tool(
                read_tool_name,
                {
                    "path": str(readme_path),
                },
            )

            print(format_result(read_result))

    except FileNotFoundError:
        raise

    except Exception as exc:
        print("\nMCP 执行失败。")
        print(f"错误类型：{type(exc).__name__}")
        print(f"错误信息：{exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())