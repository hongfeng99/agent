from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.tools import A2ATool


PROJECT_ROOT = Path(__file__).resolve().parents[3]



class LongTimeoutA2ATool(A2ATool):
    """
    支持长时间任务的 A2A 工具。

    HelloAgents 0.2.2 内置 A2AClient 的读取超时为 30 秒。
    A2A + MCP + LLM 的完整代码分析通常需要更长时间，
    因此这里将读取超时提高到 180 秒。
    """

    def __init__(
        self,
        agent_url: str,
        name: str = "a2a",
        description: str | None = None,
        timeout: int = 180,
    ) -> None:
        super().__init__(
            agent_url=agent_url,
            name=name,
            description=description,
        )

        self.timeout = timeout

    def run(
        self,
        parameters: dict[str, Any],
    ) -> str:
        """
        执行 A2A 操作。
        """

        action = str(
            parameters.get("action", "")
        ).strip().lower()

        if not action:
            return "错误：必须指定 action 参数"

        try:
            if action == "ask":
                question = str(
                    parameters.get("question", "")
                ).strip()

                if not question:
                    return "错误：必须指定 question 参数"

                response = requests.post(
                    f"{self.agent_url}/ask",
                    json={
                        "question": question,
                    },
                    # 连接超时 5 秒，读取结果最多等待 180 秒。
                    timeout=(5, self.timeout),
                )

                response.raise_for_status()

                data = response.json()
                answer = data.get(
                    "answer",
                    "远程 Agent 没有返回 answer 字段。",
                )

                return f"Agent 回答：\n{answer}"

            if action == "get_info":
                response = requests.get(
                    f"{self.agent_url}/info",
                    timeout=(5, 30),
                )

                response.raise_for_status()
                data = response.json()

                lines = ["Agent 信息："]

                for key, value in data.items():
                    lines.append(f"- {key}: {value}")

                return "\n".join(lines)

            return (
                f"错误：不支持的操作 '{action}'，"
                "只支持 ask 和 get_info。"
            )

        except requests.Timeout:
            return (
                f"错误：远程 Agent 在 {self.timeout} 秒内"
                "没有完成任务。"
            )

        except requests.RequestException as exc:
            return (
                "错误：与远程 Agent 通信失败："
                f"{type(exc).__name__}: {exc}"
            )

        except ValueError as exc:
            return f"错误：远程 Agent 返回的不是有效 JSON：{exc}"


def main() -> None:
    """
    创建 A2A 任务协调者。
    """

    load_dotenv(PROJECT_ROOT / ".env")

    print("=" * 70)
    print("Chapter 10：A2A + MCP 协调者 Agent")
    print("=" * 70)

    llm = HelloAgentsLLM()

    coordinator = SimpleAgent(
        name="任务协调者",
        llm=llm,
        system_prompt="""
        你是一个 A2A 任务协调者。

        你可以通过 code_analyst 工具，
        将代码分析任务委托给远程真实代码分析 Agent。

        远程 Agent 会通过 MCP Server 搜索和读取
        my_learning/chapter9 中的真实代码。

        调用 code_analyst 时必须遵守：

        1. 使用 action="ask"；
        2. 将完整任务放在 question 参数中；
        3. 不允许使用 action="analyze"；
        4. 不允许使用 action="inspect"。

        正确调用格式：

        {
            "action": "ask",
            "question": "分析 ContextBuilder 的主要职责和 GSSC 流程"
        }

        收到返回结果后：

        1. 检查 status 字段；
        2. status="completed" 时，整理 analysis 内容；
        3. status="incomplete" 时，明确说明分析没有完成；
        4. 检查 data_source 字段；
        5. 不要预先把远程 Agent 判断为通信演示版本；
        6. 不要把路径错误或中间状态当作真实分析结论。
        """.strip(),
    )

    code_analyst_tool = LongTimeoutA2ATool(
        name="code_analyst",
        description="""
    远程真实代码分析 Agent。

    它会通过 MCP Server 搜索和读取 Chapter 9 的真实代码。

    调用要求：
    - action 必须是 "ask"；
    - 任务放在 question 参数；
    - 不支持 analyze、inspect 等 action。

    正确示例：
    {
        "action": "ask",
        "question": "分析 ContextBuilder 的主要职责和 GSSC 流程"
    }
    """.strip(),
        agent_url="http://127.0.0.1:5001",
        timeout=180,
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