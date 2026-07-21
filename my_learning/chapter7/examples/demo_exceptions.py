from hello_agents import (
    CalculatorTool,
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistrationError,
    ToolRegistry,
)


def main() -> None:
    registry = ToolRegistry()

    calculator = CalculatorTool()

    registry.register(calculator)

    print("1. 重复注册测试：")

    try:
        registry.register(calculator)

    except ToolRegistrationError as error:
        print(
            "捕获到 ToolRegistrationError："
        )
        print(error)

    print("\n2. 工具不存在测试：")

    try:
        registry.execute_or_raise(
            name="unknown",
            parameters={},
        )

    except ToolNotFoundError as error:
        print(
            "捕获到 ToolNotFoundError："
        )
        print(error)

    print("\n3. 工具执行失败测试：")

    try:
        registry.execute_or_raise(
            name="calculator",
            parameters={
                "expression": "10 / 0",
            },
        )

    except ToolExecutionError as error:
        print(
            "捕获到 ToolExecutionError："
        )
        print(error)

    print("\n4. ReAct兼容执行方式测试：")

    result = registry.execute(
        name="calculator",
        parameters={
            "expression": "10 / 0",
        },
    )

    print("execute() 没有向外抛异常：")
    print(result)


if __name__ == "__main__":
    main()