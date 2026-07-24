import json

from hello_agents.protocols import A2AServer


# 创建一个可以被其他 Agent 调用的 A2A 服务。
code_analyst = A2AServer(
    name="code-analyst",
    description="负责分析 Python 代码结构和职责的专业智能体服务",
    version="1.0.0",
)


@code_analyst.skill("analyze")
def analyze_code_request(text: str) -> str:
    """
    处理代码分析任务。

    当前先使用固定规则模拟专业智能体。
    后续会把真实 LLM 或 MCP 代码分析能力接入这里。
    """

    # 客户端可能发送：
    #
    # analyze ContextBuilder
    #
    # 这里去掉开头的动作名称，只保留任务主体。
    task = text.strip()

    if task.lower().startswith("analyze "):
        task = task[8:].strip()

    if not task:
        return json.dumps(
            {
                "status": "failed",
                "error": "分析任务不能为空。",
            },
            ensure_ascii=False,
        )

    result = {
        "agent": "code-analyst",
        "status": "completed",
        "task": task,
        "analysis": (
            f"已经收到对“{task}”的分析任务。"
            "当前为 A2A 通信演示版本，后续将接入真实代码检索能力。"
        ),
    }

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


def main() -> None:
    """
    启动 A2A 代码分析服务。
    """

    host = "127.0.0.1"
    port = 5000

    print("=" * 70)
    print("A2A 代码分析 Agent 服务")
    print("=" * 70)
    print(f"Agent 名称：{code_analyst.name}")
    print(f"服务地址：http://{host}:{port}")
    print("可用技能：analyze")
    print("按 Ctrl + C 停止服务")
    print("=" * 70)

    # run() 会启动 HTTP 服务并持续阻塞。
    code_analyst.run(
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()