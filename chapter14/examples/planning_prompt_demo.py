from datetime import date

from chapter14.backend.prompts import (
    PLANNER_SYSTEM_PROMPT,
    build_planning_prompt,
)


def main() -> None:
    """
    演示规划阶段的系统提示词和用户提示词。
    """

    topic = "MCP 协议对智能体开发有什么价值？"

    planning_prompt = build_planning_prompt(
        topic=topic,
        current_date=date(2026, 7, 25),
    )

    print("=" * 70)
    print("系统提示词")
    print("=" * 70)
    print(PLANNER_SYSTEM_PROMPT)

    print()
    print("=" * 70)
    print("规划提示词")
    print("=" * 70)
    print(planning_prompt)


if __name__ == "__main__":
    main()