from hello_agents import (
    Config,
    HelloAgentsLLM,
    PlanAndSolveAgent,
)


def main() -> None:
    llm = HelloAgentsLLM()

    config = Config(
        temperature=0,
        max_tokens=1200,
        max_history_length=20,
        max_steps=5,
        debug=True,
    )

    agent = PlanAndSolveAgent(
        name="规划执行助手",
        llm=llm,
        system_prompt=(
            "你是一位擅长拆解复杂任务并逐步解决问题的助手。"
            "请保证分析清晰、结果准确。"
        ),
        config=config,
    )

    question = (
        "一个书店周一卖出125本书，"
        "周二比周一多卖出20%，"
        "周三比周二少卖出15本。"
        "请计算三天总共卖出多少本书，"
        "并说明计算过程。"
    )

    result = agent.run(question)

    print("\n====================")
    print("最终回答：")
    print(result)

    print("\n====================")
    print("生成的计划：")

    for index, step in enumerate(
        agent.last_plan,
        start=1,
    ):
        print(f"{index}. {step}")

    print("\n====================")
    print("各步骤执行结果：")

    for index, step_result in enumerate(
        agent.last_step_results,
        start=1,
    ):
        print(f"\n第 {index} 步：")
        print(step_result)


if __name__ == "__main__":
    main()