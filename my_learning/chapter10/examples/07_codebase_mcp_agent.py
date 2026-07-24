import sys
from pathlib import Path

from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.tools import MCPTool


# 当前文件位于：
#
# hello-agents/
# └── my_learning/
#     └── chapter10/
#         └── examples/
#             └── 07_codebase_mcp_agent.py
#
# parents[3] 是 hello-agents 项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 自定义 MCP Server 与当前文件位于同一个目录。
SERVER_SCRIPT = Path(__file__).with_name(
    "05_codebase_mcp_server.py"
).resolve()


def check_environment() -> None:
    """
    检查运行程序需要的目录和文件。
    """

    if not PROJECT_ROOT.exists():
        raise FileNotFoundError(
            f"找不到项目根目录：{PROJECT_ROOT}"
        )

    if not SERVER_SCRIPT.exists():
        raise FileNotFoundError(
            f"找不到 MCP Server：{SERVER_SCRIPT}"
        )

    chapter9_directory = PROJECT_ROOT / "my_learning" / "chapter9"

    if not chapter9_directory.exists():
        raise FileNotFoundError(
            f"找不到 Chapter 9 目录：{chapter9_directory}"
        )


def create_agent() -> SimpleAgent:
    """
    创建代码库分析智能体。
    """

    # 加载项目根目录中的 .env。
    load_dotenv(PROJECT_ROOT / ".env")

    # 创建模型客户端。
    llm = HelloAgentsLLM()

    # 创建智能体。
    agent = SimpleAgent(
        name="代码库分析助手",
        llm=llm,
        system_prompt="""
            你是一名严谨的 Python 代码库分析助手。

            你可以通过 MCP 工具查看当前 hello-agents 项目的真实代码。

            处理代码分析问题时，必须遵守以下要求：

            1. 不要根据记忆猜测代码实现；
            2. 首先使用代码搜索工具定位相关类、函数或关键字；
            3. 找到相关文件后，使用源码读取工具查看实际代码；
            4. 如果一段代码不足以得出结论，应继续读取相关范围或相关文件；
            5. 回答中必须明确区分：
            - 代码中已经实现的功能；
            - 根据代码进行的合理推断；
            - 当前代码尚未实现的功能；
            6. 不得声称读取了实际上没有调用工具查看的文件；
            7. 只允许查看和分析代码，不得修改、删除或执行项目文件；
            8. 最终使用中文回答；
            9. 最终回答应包含：
            - 主要职责；
            - 执行流程；
            - 当前实现的局限；
            - 简要总结。
            10. 你可以连续调用多个工具，直到获得足够信息；
            11. 如果第一次读取没有覆盖完整类定义，必须继续读取后续行；
            12. 搜索结果只能用于定位文件，不能替代完整源码读取；
            13. 获得足够证据后，必须直接输出完整答案，不要只说明“还需要继续读取”；
            14. 即使工具调用次数接近上限，也应根据已经读取的代码给出当前能够支持的完整结论，并明确不确定部分。
            

            可用代码库工具包括：
            - 获取项目摘要；
            - 列出 Python 文件；
            - 搜索类名、函数名和关键字；
            - 按行读取源码文件。
            """.strip(),
    )

    # 将自定义 MCP Server 封装成 MCPTool。
    codebase_tool = MCPTool(
        name="codebase",
        description=(
            "安全查看和分析当前 hello-agents Python 项目的真实代码"
        ),
        server_command=[
            sys.executable,
            str(SERVER_SCRIPT),
        ],
    )

    # 添加 MCPTool。
    #
    # 添加后，服务器中的工具会被展开成：
    #
    # codebase_get_project_summary
    # codebase_list_python_files
    # codebase_search_symbol
    # codebase_read_source_file
    agent.add_tool(codebase_tool)

    return agent


def main() -> None:
    """
    运行代码库 MCP Agent 实验。
    """

    check_environment()

    print("=" * 72)
    print("Chapter 10：自定义 MCP 代码库分析智能体")
    print("=" * 72)
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"MCP Server：{SERVER_SCRIPT}")

    agent = create_agent()

    question = """
        请根据 my_learning/chapter9 中的真实代码分析 ContextBuilder。

        请按照以下顺序执行：

        1. 使用 codebase_search_symbol 搜索 ContextBuilder；
        2. 找到定义文件后，使用 codebase_read_source_file 阅读完整类定义；
        3. 如果第一次读取没有覆盖完整类，请继续读取后续行；
        4. 搜索并阅读 Gather、Select、Structure、Compress 对应的方法；
        5. 必要时继续读取 ContextPackage 等相关类；
        6. 收集足够信息后输出最终分析。

        最终回答必须包含：

        一、ContextBuilder 的主要职责；
        二、Gather、Select、Structure、Compress 的完整执行流程；
        三、每个阶段调用的主要方法；
        四、当前实现的局限；
        五、总结。

        不要只回答“需要继续读取代码”。
        """.strip()

    print("\n" + "=" * 72)
    print("用户问题")
    print("=" * 72)
    print(question)

    print("\n" + "=" * 72)
    print("开始运行智能体")
    print("=" * 72)

    response = agent.run(
        question,
        max_tool_iterations=8,
    )

    print("\n" + "=" * 72)
    print("智能体最终回答")
    print("=" * 72)
    print(response)


if __name__ == "__main__":
    main()