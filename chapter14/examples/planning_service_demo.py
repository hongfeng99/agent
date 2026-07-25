from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

from chapter14.backend.services.planning_service import (
    PlanningService,
)


def print_tasks(tasks: list) -> None:
    """
    打印研究规划结果。
    """

    print()
    print(f"共生成 {len(tasks)} 个研究子任务：")

    for task in tasks:
        print()
        print("-" * 70)
        print(f"任务 {task.id}：{task.title}")
        print(f"研究目的：{task.intent}")
        print(f"搜索语句：{task.query}")
        print(f"当前状态：{task.status.value}")


def main() -> None:
    """
    使用真实大模型生成研究计划。
    """

    # 从项目根目录的 .env 文件读取模型配置。
    load_dotenv()

    llm = HelloAgentsLLM()

    planning_service = PlanningService(
        llm=llm,
        min_tasks=3,
        max_tasks=5,
    )

    topic = (
        "MCP 协议对智能体开发有什么价值？"
    )

    print("=" * 70)
    print("Deep Research Agent：研究规划阶段")
    print("=" * 70)
    print(f"研究主题：{topic}")
    print()
    print("正在调用大模型生成研究计划……")

    try:
        tasks = planning_service.plan(topic)
    except Exception as exc:
        print()
        print("研究规划失败。")
        print(f"异常类型：{type(exc).__name__}")
        print(f"异常信息：{exc}")
        raise

    print_tasks(tasks)

    print()
    print("=" * 70)
    print("研究规划完成")
    print("=" * 70)


if __name__ == "__main__":
    main()