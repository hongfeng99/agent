import shutil
from pathlib import Path

from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.tools import MCPTool


# 加载项目根目录中的 .env
load_dotenv()


def find_npx_command() -> str:
    """
    查找当前系统中的 npx 命令。

    Windows 一般是 npx.cmd；
    其他系统一般是 npx。
    """

    npx_command = shutil.which("npx.cmd") or shutil.which("npx")

    if npx_command is None:
        raise RuntimeError(
            "没有找到 npx，请先安装 Node.js，"
            "并确认 npx --version 可以正常运行。"
        )

    return npx_command


def main() -> None:
    """
    创建一个能够自动读取项目文件的智能体。
    """

    # 当前程序需要从 hello-agents 项目根目录运行。
    project_root = Path.cwd().resolve()
    readme_path = project_root / "README.md"

    if not readme_path.exists():
        raise FileNotFoundError(
            f"没有找到项目 README.md：{readme_path}\n"
            "请在 hello-agents 项目根目录运行程序。"
        )

    print("=" * 70)
    print("MCP 文件系统智能体")
    print("=" * 70)
    print(f"项目根目录：{project_root}")

    # 1. 创建大模型客户端
    llm = HelloAgentsLLM()

    # 2. 创建智能体
    agent = SimpleAgent(
        name="项目文档助手",
        llm=llm,
        system_prompt="""
            你是一个项目文档分析助手。

            你的任务是根据用户的问题读取项目中的真实文件，并基于文件内容回答。

            要求：
            1. 需要了解文件内容时，必须调用文件系统工具；
            2. 不要编造未读取到的信息；
            3. 只允许读取文件和查看目录；
            4. 不要写入、移动、删除或修改任何文件；
            5. 回答使用中文；
            6. 最终回答要结构清晰、简洁准确。
            """.strip(),
    )

    # 3. 创建文件系统 MCP 工具
    filesystem_tool = MCPTool(
        name="filesystem",
        description="读取和查看当前 hello-agents 项目中的文件",
        server_command=[
            find_npx_command(),
            "-y",
            "@modelcontextprotocol/server-filesystem",
            str(project_root),
        ],
    )

    # 4. 添加 MCPTool
    #
    # 添加时，HelloAgents 会连接 MCP Server，
    # 获取服务器工具，并展开成 Agent 可以直接调用的工具。
    agent.add_tool(filesystem_tool)

    print("\nMCP 文件系统工具添加成功。")
    print("开始向智能体提出问题……")
    print("-" * 70)

    # 5. 提出需要读取真实文件才能回答的问题
    question = """
        请读取项目根目录中的 README.md，然后回答：

        1. Hello-Agents 是什么项目？
        2. 这个项目希望帮助学习者获得什么能力？
        3. 项目的主要学习内容有哪些？

        只能根据 README.md 的真实内容回答。
        """.strip()

    print(f"用户问题：\n{question}")
    print("\n" + "-" * 70)

    # 6. Agent 自主判断并调用 MCP 文件工具
    response = agent.run(question)

    print("\n智能体回答：")
    print("=" * 70)
    print(response)


if __name__ == "__main__":
    main()