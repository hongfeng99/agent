from typing import Any, Dict

from hello_agents import (
    CalculatorTool,
    ToolChain,
    ToolChainManager,
    ToolRegistry,
)


def build_first_parameters(
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    第一步参数构造函数。

    从初始上下文中读取 expression，
    交给 calculator 工具。
    """

    return {
        "expression": context["expression"],
    }


def build_second_parameters(
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    第二步参数构造函数。

    读取第一步结果 first_result，
    再乘以初始上下文中的 multiplier。
    """

    first_result = context["first_result"]
    multiplier = context["multiplier"]

    return {
        "expression": (
            f"{first_result} * {multiplier}"
        ),
    }


def main() -> None:
    # 1. 创建工具注册表
    registry = ToolRegistry()

    # 2. 注册计算器工具
    registry.register(
        CalculatorTool()
    )

    # 3. 创建工具链
    chain = ToolChain(
        name="double_calculation",
        description=(
            "先计算原始表达式，"
            "再将结果乘以指定倍数。"
        ),
        tool_registry=registry,
    )

    # 4. 添加第一个步骤
    chain.add_step(
        name="计算原始表达式",
        tool_name="calculator",
        parameter_builder=build_first_parameters,
        output_key="first_result",
    )

    # 5. 添加第二个步骤
    chain.add_step(
        name="将第一次结果乘以指定倍数",
        tool_name="calculator",
        parameter_builder=build_second_parameters,
        output_key="final_result",
    )

    # 6. 创建工具链管理器
    manager = ToolChainManager()

    # 7. 注册工具链
    manager.register(chain)

    print("工具链数量：")
    print(len(manager))

    print("\n是否存在 double_calculation：")
    print("double_calculation" in manager)

    print("\n工具链步骤：")

    for index, step in enumerate(
        chain.list_steps(),
        start=1,
    ):
        print(
            f"{index}. "
            f"{step.name} "
            f"-> {step.tool_name} "
            f"-> {step.output_key}"
        )

    # 8. 执行工具链
    context = manager.execute(
        name="double_calculation",
        initial_context={
            "expression": "(12 + 8) * 3",
            "multiplier": 2,
        },
    )

    print("\n第一次计算结果：")
    print(context["first_result"])

    print("\n最终计算结果：")
    print(context["final_result"])

    print("\n完整上下文：")
    print(context)

    print("\n执行轨迹：")

    for record in context["_execution_trace"]:
        print(
            f"第 {record['step_number']} 步："
            f"{record['step_name']}"
        )
        print(
            f"调用工具：{record['tool_name']}"
        )
        print(
            f"工具参数：{record['parameters']}"
        )
        print(
            f"执行结果：{record['result']}"
        )
        print()


if __name__ == "__main__":
    main()