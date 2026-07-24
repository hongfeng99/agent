import json
from typing import Any

from hello_agents.protocols import A2AClient


def format_result(result: Any) -> str:
    """
    尝试格式化 A2A 返回结果。
    """

    if isinstance(result, str):
        try:
            data = json.loads(result)

            return json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
        except json.JSONDecodeError:
            return result

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def main() -> None:
    """
    使用 A2AClient 调用代码分析 Agent。
    """

    agent_url = "http://127.0.0.1:5000"

    print("=" * 70)
    print("A2A 代码分析客户端")
    print("=" * 70)
    print(f"连接地址：{agent_url}")

    # 创建连接远程 Agent 的客户端。
    client = A2AClient(agent_url)

    task = "analyze ContextBuilder 的主要职责和 GSSC 流程"

    print("\n发送任务：")
    print(task)

    # 指定远程 Agent 的技能名称和输入内容。
    response = client.execute_skill(
        "analyze",
        task,
    )

    print("\n原始 A2A 响应：")
    print(response)

    # execute_skill 通常返回包含 result 字段的字典。
    if isinstance(response, dict):
        result = response.get("result", response)
    else:
        result = response

    print("\nAgent 返回结果：")
    print(format_result(result))


if __name__ == "__main__":
    main()