from pathlib import Path

from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.protocols import (
    ANPDiscovery,
    register_service,
)
from hello_agents.tools import ANPTool


# 当前文件位于：
#
# hello-agents/
# └── my_learning/
#     └── chapter10/
#         └── examples/
#             └── 14_anp_scheduler_agent.py
#
# parents[3] 对应项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def register_demo_services(
    discovery: ANPDiscovery,
) -> None:
    """
    向当前 ANP 服务发现中心注册三个示例服务。

    注意：
    ANPDiscovery 当前是内存实现。
    13_anp_service_discovery.py 中注册的服务，
    不会自动保留到这个新进程中。
    """

    # 普通代码分析演示服务。
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

    # 能通过 MCP 读取真实代码的服务。
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

    # 文档撰写服务。
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


def main() -> None:
    """
    创建能够通过 ANP 自动发现和选择服务的调度 Agent。
    """

    load_dotenv(PROJECT_ROOT / ".env")

    print("=" * 72)
    print("Chapter 10：ANP 智能服务调度 Agent")
    print("=" * 72)

    # --------------------------------------------------
    # 第一步：创建服务发现中心
    # --------------------------------------------------

    discovery = ANPDiscovery()

    # 每个 Python 进程都需要重新注册服务。
    register_demo_services(discovery)

    services = discovery.list_all_services()

    print(
        f"当前 ANP 发现中心共注册 "
        f"{len(services)} 个服务。"
    )

    # --------------------------------------------------
    # 第二步：创建任务调度 Agent
    # --------------------------------------------------

    llm = HelloAgentsLLM()

    scheduler = SimpleAgent(
        name="ANP任务调度器",
        llm=llm,
        system_prompt="""
你是一个智能体服务调度器。

你的职责不是亲自执行代码分析任务，
而是通过 ANP 服务发现工具找到最适合的远程 Agent。

处理代码分析任务时，必须遵守：

1. 必须调用 service_discovery 工具；
2. 查询代码分析服务时必须使用：
   action="discover_services"
   service_type="code_analysis"
3. 不允许使用 register_service、add_node
   或其他与当前任务无关的操作；
4. 收到候选服务列表后，比较：
   - capabilities；
   - metadata 中的 real_code_access；
   - metadata 中的 load；
   - endpoint；
5. 如果任务要求分析真实代码，
   应优先选择具备 mcp_code_reading 能力，
   且 real_code_access=True 的服务；
6. 在能力满足要求的前提下，
   优先选择负载更低的服务；
7. 最终必须说明：
   - 找到了哪些候选服务；
   - 使用了哪些选择标准；
   - 最终选择了哪个服务；
   - 该服务的 endpoint；
8. 当前步骤只负责服务发现和选择，
   不要声称已经通过 A2A 执行了远程任务。
""".strip(),
    )

    # --------------------------------------------------
    # 第三步：创建并添加 ANPTool
    # --------------------------------------------------

    service_discovery_tool = ANPTool(
        name="service_discovery",
        description="""
ANP 服务发现工具。

当前工具中已经注册了多个智能体服务。

代码分析任务的正确调用格式：

{
    "action": "discover_services",
    "service_type": "code_analysis"
}

工具会返回候选服务的：
- service_id；
- service_name；
- service_type；
- endpoint；
- capabilities；
- metadata。
""".strip(),
        discovery=discovery,
    )

    scheduler.add_tool(
        service_discovery_tool
    )

    print(
        "ANP 服务发现工具已添加到调度 Agent。"
    )

    # --------------------------------------------------
    # 第四步：提交自然语言调度任务
    # --------------------------------------------------

    question = """
我需要分析 my_learning/chapter9 中
ContextBuilder 的真实源码和 GSSC 流程。

请为这个任务选择最合适的远程 Agent。

你必须先调用 service_discovery 工具，并使用：

action = "discover_services"
service_type = "code_analysis"

然后完成：

1. 列出发现的所有代码分析服务；
2. 比较各服务的能力、真实代码访问能力和负载；
3. 选择最合适的服务；
4. 给出 service_id、服务名称和 endpoint；
5. 说明选择理由；
6. 明确说明本次只完成服务选择，
   尚未真正执行远程分析任务。
""".strip()

    print("\n" + "=" * 72)
    print("用户任务")
    print("=" * 72)
    print(question)

    response = scheduler.run(
        question,
        max_tool_iterations=4,
    )

    print("\n" + "=" * 72)
    print("ANP 调度结果")
    print("=" * 72)
    print(response)


if __name__ == "__main__":
    main()