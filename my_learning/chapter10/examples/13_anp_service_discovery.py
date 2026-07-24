from typing import Any

from hello_agents.protocols import (
    ANPDiscovery,
    ANPNetwork,
    discover_service,
    register_service,
)


def print_service(service: Any) -> None:
    """
    打印一个 ANP 服务的信息。
    """

    print(f"服务 ID：{service.service_id}")
    print(f"服务名称：{service.service_name}")
    print(f"服务类型：{service.service_type}")
    print(f"能力：{service.capabilities}")
    print(f"地址：{service.endpoint}")
    print(f"元数据：{service.metadata}")


def main() -> None:
    """
    演示 ANP 的服务注册、服务发现和简单路由。
    """

    print("=" * 70)
    print("Chapter 10：ANP 服务发现实验")
    print("=" * 70)

    # 1. 创建服务发现中心。
    discovery = ANPDiscovery()

    # 2. 注册普通代码分析 Agent。
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

    # 3. 注册具备 MCP 能力的真实代码分析 Agent。
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

    # 4. 注册文档撰写 Agent。
    register_service(
        discovery=discovery,
        service_id="documentation_writer",
        service_name="技术文档撰写 Agent",
        service_type="documentation",
        capabilities=[
            "documentation",
            "report_generation",
        ],
        endpoint="http://127.0.0.1:5002",
        metadata={
            "load": 0.4,
            "version": "1.0.0",
        },
    )

    print("\n[步骤 1] 服务注册完成")

    all_services = discovery.list_all_services()

    print(f"当前共注册 {len(all_services)} 个服务。")

    # 5. 查看全部服务。
    print("\n" + "=" * 70)
    print("[步骤 2] 查看全部服务")
    print("=" * 70)

    for index, service in enumerate(
        all_services,
        start=1,
    ):
        print(f"\n服务 {index}")
        print("-" * 40)
        print_service(service)

    # 6. 按服务类型发现代码分析 Agent。
    print("\n" + "=" * 70)
    print("[步骤 3] 发现代码分析服务")
    print("=" * 70)

    code_services = discover_service(
        discovery,
        service_type="code_analysis",
    )

    print(
        f"共发现 {len(code_services)} "
        "个代码分析服务。"
    )

    for service in code_services:
        load = service.metadata.get(
            "load",
            1.0,
        )

        print(
            f"- {service.service_name}，"
            f"负载：{load}"
        )

    if not code_services:
        raise RuntimeError(
            "没有发现代码分析服务。"
        )

    # 7. 选择负载最低的服务。
    best_service = min(
        code_services,
        key=lambda service: service.metadata.get(
            "load",
            1.0,
        ),
    )

    print("\n" + "=" * 70)
    print("[步骤 4] 负载路由结果")
    print("=" * 70)

    print("选择的最佳代码分析服务：")
    print_service(best_service)

    # 8. 根据能力筛选真实代码服务。
    real_code_services = [
        service
        for service in code_services
        if "mcp_code_reading"
        in service.capabilities
    ]

    print("\n" + "=" * 70)
    print("[步骤 5] 按能力筛选")
    print("=" * 70)

    print(
        "支持 MCP 真实代码读取的服务数量："
        f"{len(real_code_services)}"
    )

    for service in real_code_services:
        print(
            f"- {service.service_name}："
            f"{service.endpoint}"
        )

    # 9. 构建简单 Agent 网络。
    network = ANPNetwork(
        network_id="chapter10_agent_network"
    )

    for service in all_services:
        network.add_node(
            service.service_id,
            service.endpoint,
        )

    # 表示真实代码分析结果可以交给文档撰写服务。
    network.connect_nodes(
        "real_code_analyst",
        "documentation_writer",
    )

    stats = network.get_network_stats()

    print("\n" + "=" * 70)
    print("[步骤 6] Agent 网络统计")
    print("=" * 70)

    print(f"网络统计：{stats}")

    print("\n" + "=" * 70)
    print("ANP 服务发现实验完成")
    print("=" * 70)


if __name__ == "__main__":
    main()