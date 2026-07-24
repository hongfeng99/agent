import json
from typing import Any

import requests

from hello_agents.protocols import (
    ANPDiscovery,
    discover_service,
    register_service,
)


def register_services(
    discovery: ANPDiscovery,
) -> None:
    """
    注册可供 ANP 发现的代码分析服务。

    当前注册两个服务：

    1. 演示版代码分析 Agent；
    2. 能通过 MCP 读取真实代码的 Agent。
    """

    register_service(
        discovery=discovery,
        service_id="code_analyst_demo",
        service_name="代码分析演示 Agent",
        service_type="code_analysis",
        capabilities=[
            "task_receiving",
            "code_analysis_demo",
        ],
        endpoint="http://127.0.0.1:5000",
        metadata={
            "load": 0.6,
            "version": "1.0.0",
            "real_code_access": False,
        },
    )

    register_service(
        discovery=discovery,
        service_id="real_code_analyst",
        service_name="真实代码分析 Agent",
        service_type="code_analysis",
        capabilities=[
            "code_analysis",
            "mcp_code_reading",
            "gssc_analysis",
        ],
        endpoint="http://127.0.0.1:5001",
        metadata={
            "load": 0.2,
            "version": "1.0.0",
            "real_code_access": True,
        },
    )


def select_best_service(
    discovery: ANPDiscovery,
) -> Any:
    """
    通过 ANP 发现并选择最适合真实代码分析的服务。

    选择规则：

    1. service_type 必须是 code_analysis；
    2. 必须具备 mcp_code_reading；
    3. real_code_access 必须是 True；
    4. 在满足能力要求的服务中选择负载最低者。
    """

    services = discover_service(
        discovery,
        service_type="code_analysis",
    )

    if not services:
        raise RuntimeError(
            "ANP 没有发现 code_analysis 服务。"
        )

    print(f"[ANP] 共发现 {len(services)} 个代码分析服务。")

    for service in services:
        print(
            f"[ANP] 候选服务：{service.service_id}，"
            f"endpoint={service.endpoint}，"
            f"load={service.metadata.get('load')}"
        )

    qualified_services = [
        service
        for service in services
        if (
            "mcp_code_reading"
            in service.capabilities
            and service.metadata.get(
                "real_code_access",
                False,
            )
        )
    ]

    if not qualified_services:
        raise RuntimeError(
            "没有找到支持 MCP 真实代码读取的服务。"
        )

    best_service = min(
        qualified_services,
        key=lambda service: service.metadata.get(
            "load",
            1.0,
        ),
    )

    return best_service


def parse_agent_answer(
    response_data: dict[str, Any],
) -> dict[str, Any]:
    """
    解析 A2A /ask 接口返回的数据。

    A2A Server 通常返回：

    {
        "answer": "{...JSON字符串...}"
    }
    """

    answer = response_data.get("answer")

    if isinstance(answer, dict):
        return answer

    if isinstance(answer, str):
        try:
            parsed = json.loads(answer)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "远程 Agent 的 answer 不是有效 JSON。"
            ) from exc

        if not isinstance(parsed, dict):
            raise TypeError(
                "远程 Agent 的 JSON 结果不是对象。"
            )

        return parsed

    raise TypeError(
        "A2A 响应中没有有效的 answer 字段。"
    )


def send_a2a_task(
    endpoint: str,
    task: str,
    timeout: int = 180,
) -> dict[str, Any]:
    """
    通过 A2A 向选中的远程 Agent 发送任务。

    连接最多等待 5 秒；
    远程分析结果最多等待 timeout 秒。
    """

    ask_url = f"{endpoint.rstrip('/')}/ask"

    print(f"[A2A] 正在向 {ask_url} 发送任务……")

    try:
        response = requests.post(
            ask_url,
            json={
                "question": task,
            },
            timeout=(5, timeout),
        )

        response.raise_for_status()

    except requests.Timeout as exc:
        raise TimeoutError(
            f"远程 Agent 在 {timeout} 秒内"
            "没有完成任务。"
        ) from exc

    except requests.RequestException as exc:
        raise ConnectionError(
            "A2A 通信失败："
            f"{type(exc).__name__}: {exc}"
        ) from exc

    response_data = response.json()

    if not isinstance(response_data, dict):
        raise TypeError(
            "A2A 响应的顶层数据不是对象。"
        )

    return parse_agent_answer(response_data)


def validate_result(
    result: dict[str, Any],
) -> None:
    """
    验证远程分析结果是否真正完成。
    """

    status = result.get("status")

    if status != "completed":
        reasons = (
            result
            .get("validation", {})
            .get("reasons", [])
        )

        raise RuntimeError(
            "远程分析没有完整完成。\n"
            f"status={status}\n"
            f"reasons={reasons}\n"
            f"analysis={result.get('analysis')}"
        )

    symbols_read = result.get(
        "symbols_read",
        [],
    )

    expected_symbols = {
        "ContextBuilder.build",
        "ContextBuilder._gather",
        "ContextBuilder._select",
        "ContextBuilder._structure",
        "ContextBuilder._compress",
    }

    missing_symbols = (
        expected_symbols
        - set(symbols_read)
    )

    if missing_symbols:
        raise RuntimeError(
            "远程 Agent 没有读取完整的 GSSC 方法："
            f"{sorted(missing_symbols)}"
        )


def main() -> None:
    """
    完成 ANP + A2A + MCP 端到端协议实验。
    """

    print("=" * 72)
    print("Chapter 10：ANP + A2A + MCP 完整协议链路")
    print("=" * 72)

    # --------------------------------------------------
    # 第一步：ANP 服务注册
    # --------------------------------------------------

    discovery = ANPDiscovery()
    register_services(discovery)

    print("\n[步骤 1] ANP 服务注册完成")

    # --------------------------------------------------
    # 第二步：ANP 服务发现与选择
    # --------------------------------------------------

    print("\n" + "=" * 72)
    print("[步骤 2] ANP 发现并选择服务")
    print("=" * 72)

    best_service = select_best_service(
        discovery
    )

    print("\n[ANP] 最终选择：")
    print(f"服务 ID：{best_service.service_id}")
    print(f"服务名称：{best_service.service_name}")
    print(f"服务地址：{best_service.endpoint}")
    print(f"能力：{best_service.capabilities}")
    print(f"元数据：{best_service.metadata}")

    # --------------------------------------------------
    # 第三步：通过 A2A 委托任务
    # --------------------------------------------------

    task = (
        "分析 ContextBuilder 的主要职责和 "
        "GSSC 流程。"
    )

    print("\n" + "=" * 72)
    print("[步骤 3] A2A 发送任务")
    print("=" * 72)
    print(f"任务：{task}")

    result = send_a2a_task(
        endpoint=best_service.endpoint,
        task=task,
        timeout=180,
    )

    # --------------------------------------------------
    # 第四步：验证 MCP 真实代码结果
    # --------------------------------------------------

    print("\n" + "=" * 72)
    print("[步骤 4] 验证远程分析结果")
    print("=" * 72)

    validate_result(result)

    print(f"Agent：{result.get('agent')}")
    print(f"状态：{result.get('status')}")
    print(f"耗时：{result.get('elapsed_seconds')} 秒")
    print(f"数据来源：{result.get('data_source')}")
    print("读取的符号：")

    for symbol in result.get(
        "symbols_read",
        [],
    ):
        print(f"- {symbol}")

    # --------------------------------------------------
    # 第五步：输出真实代码分析
    # --------------------------------------------------

    print("\n" + "=" * 72)
    print("[步骤 5] ContextBuilder 分析结果")
    print("=" * 72)

    print(result.get("analysis"))

    print("\n" + "=" * 72)
    print("完整协议链路测试成功")
    print("=" * 72)
    print("ANP：成功发现并选择 real_code_analyst")
    print("A2A：成功发送并接收远程任务")
    print("MCP：成功读取 Chapter 9 真实代码")
    print("LLM：成功生成完整 GSSC 分析")


if __name__ == "__main__":
    main()