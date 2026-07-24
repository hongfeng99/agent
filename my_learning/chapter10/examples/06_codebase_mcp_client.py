import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from hello_agents.protocols import MCPClient


def parse_json_result(result: Any) -> dict[str, Any]:
    """
    将 MCP 工具返回结果解析为字典。
    """

    if isinstance(result, str):
        return json.loads(result)

    raise TypeError(
        f"预期 MCP 返回字符串，实际得到："
        f"{type(result).__name__}"
    )


async def main() -> None:
    """
    测试自定义代码库 MCP Server。
    """

    server_script = Path(__file__).with_name(
        "05_codebase_mcp_server.py"
    ).resolve()

    if not server_script.exists():
        raise FileNotFoundError(
            f"找不到 MCP Server：{server_script}"
        )

    # sys.executable 是当前 Conda 环境中的 Python。
    #
    # 比直接写 "python" 更可靠，能够确保 Server 和 Client
    # 使用同一个 Python 环境及依赖。
    client = MCPClient(
        [
            sys.executable,
            str(server_script),
        ]
    )

    async with client:
        print("=" * 70)
        print("步骤 1：发现自定义 MCP 工具")
        print("=" * 70)

        tools = await client.list_tools()

        for index, tool in enumerate(tools, start=1):
            print(f"\n{index}. {tool['name']}")
            print(f"   描述：{tool.get('description', '无描述')}")

        print("\n" + "=" * 70)
        print("步骤 2：获取项目摘要")
        print("=" * 70)

        summary_result = await client.call_tool(
            "get_project_summary",
            {},
        )

        summary = parse_json_result(summary_result)
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        print("\n" + "=" * 70)
        print("步骤 3：列出 Chapter 9 的 Python 文件")
        print("=" * 70)

        files_result = await client.call_tool(
            "list_python_files",
            {
                "relative_directory": "my_learning/chapter9",
                "max_results": 100,
            },
        )

        files = parse_json_result(files_result)
        print(json.dumps(files, ensure_ascii=False, indent=2))

        print("\n" + "=" * 70)
        print("步骤 4：搜索 ContextBuilder")
        print("=" * 70)

        search_result = await client.call_tool(
            "search_symbol",
            {
                "keyword": "ContextBuilder",
                "relative_directory": "my_learning/chapter9",
                "max_results": 20,
            },
        )

        search_data = parse_json_result(search_result)
        print(
            json.dumps(
                search_data,
                ensure_ascii=False,
                indent=2,
            )
        )

        # 找到结果后，读取第一处匹配文件附近的代码。
        matches = search_data.get("matches", [])

        if matches:
            first_match = matches[0]
            source_path = first_match["path"]
            line_number = first_match["line_number"]

            start_line = max(1, line_number - 10)
            end_line = line_number + 40

            print("\n" + "=" * 70)
            print(f"步骤 5：读取源码 {source_path}")
            print("=" * 70)

            source_result = await client.call_tool(
                "read_source_file",
                {
                    "path": source_path,
                    "start_line": start_line,
                    "end_line": end_line,
                },
            )

            source_data = parse_json_result(source_result)
            print(source_data["content"])
        else:
            print("\n没有搜索到 ContextBuilder。")

        # -------------------------------------------------
        # 步骤 6：精确读取 GSSC 相关方法
        # -------------------------------------------------
        print("\n" + "=" * 70)
        print("步骤 6：精确读取 ContextBuilder 的 GSSC 方法")
        print("=" * 70)

        symbols = [
            "ContextBuilder.build",
            "ContextBuilder._gather",
            "ContextBuilder._select",
            "ContextBuilder._structure",
            "ContextBuilder._compress",
        ]

        for symbol in symbols:
            print("\n" + "-" * 70)
            print(f"读取符号：{symbol}")
            print("-" * 70)

            symbol_result = await client.call_tool(
                "read_python_symbol",
                {
                    "path": (
                        "my_learning/chapter9/"
                        "context/builder.py"
                    ),
                    "symbol": symbol,
                },
            )

            symbol_data = parse_json_result(symbol_result)
            print(symbol_data["content"])


if __name__ == "__main__":
    asyncio.run(main())