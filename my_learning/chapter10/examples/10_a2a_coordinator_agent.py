from pathlib import Path

from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.tools import A2ATool


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    """
    创建 A2A 任务协调者。
    """

    load_dotenv(PROJECT_ROOT / ".env")

    print("=" * 70)
    print("Chapter 10：A2A 协调者 Agent")
    print("=" * 70)

    llm = HelloAgentsLLM()

    coordinator = SimpleAgent(
        name="任务协调者",
        llm=llm,
        system_prompt="""
你是一个任务协调者。

你可以通过 code_analyst 工具，把代码分析任务委托给远程 Agent。

调用 code_analyst 时必须严格遵守：

1. 代码分析任务必须使用 action="ask"；
2. 将完整任务放进 question 参数；
3. 不允许使用 action="analyze"；
4. 不允许使用 action="inspect"；
5. action 只允许是 "ask" 或 "get_info"。

正确调用格式：

{
    "action": "ask",
    "question": "完整的代码分析任务"
}

收到远程结果后，请说明：
1. 任务是否发送成功；
2. 远程 Agent 返回了什么；
3. 返回结果是否属于真实代码分析。

当前远程 Agent 只是通信演示版本，
不要把固定回复当成真实源码分析结论。
""".strip(),
    )

    code_analyst_tool = A2ATool(
        name="code_analyst",
        description="""
远程代码分析 Agent。

调用规则：
- 分析任务必须使用 action="ask"；
- 分析要求放在 question 参数中；
- action 只允许 ask 或 get_info；
- 不支持 analyze、inspect 等 action。

正确参数示例：
{
    "action": "ask",
    "question": "分析 ContextBuilder 的主要职责"
}
""".strip(),
        agent_url="http://127.0.0.1:5000",
    )

    coordinator.add_tool(code_analyst_tool)

    print("远程 code-analyst Agent 已添加为 A2A 工具。")

    question = """
请务必调用 code_analyst 工具，把下面的任务发送给远程 Agent：

分析 ContextBuilder 的主要职责和 GSSC 流程。

调用参数必须严格为：

action = "ask"

question = "分析 ContextBuilder 的主要职责和 GSSC 流程"

不要使用 analyze、inspect 或其他 action。

收到结果后，请告诉我：
1. 任务是否发送成功；
2. 远程 Agent 返回了什么；
3. 当前结果是否属于真实代码分析。
""".strip()

    print("\n" + "=" * 70)
    print("用户问题")
    print("=" * 70)
    print(question)

    response = coordinator.run(
        question,
        max_tool_iterations=4,
    )

    print("\n" + "=" * 70)
    print("协调者最终回答")
    print("=" * 70)
    print(response)


if __name__ == "__main__":
    main()