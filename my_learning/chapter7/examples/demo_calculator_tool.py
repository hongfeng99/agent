from hello_agents.tools import (
    CalculatorTool,
    ToolRegistry,
)


def main() -> None:
    registry = ToolRegistry()

    calculator = CalculatorTool()

    registry.register(calculator)

    test_expressions = [
        "1 + 2",
        "(12 + 8) * 3",
        "100 / 4",
        "10 // 3",
        "10 % 3",
        "2 ** 8",
        "-5 + 12",
    ]

    print("正常计算测试：")

    for expression in test_expressions:
        result = registry.execute(
            name="calculator",
            parameters={
                "expression": expression,
            },
        )

        print(f"{expression} = {result}")

    print("\n除零错误测试：")

    divide_by_zero_result = registry.execute(
        name="calculator",
        parameters={
            "expression": "10 / 0",
        },
    )

    print(divide_by_zero_result)

    print("\n非法函数调用测试：")

    unsafe_result = registry.execute(
        name="calculator",
        parameters={
            "expression": "__import__('os').listdir('.')",
        },
    )

    print(unsafe_result)

    print("\n缺少参数测试：")

    missing_parameter_result = registry.execute(
        name="calculator",
        parameters={},
    )

    print(missing_parameter_result)

    print("\n工具说明：")
    print(registry.get_tools_description())


if __name__ == "__main__":
    main()