import ast
import math
import operator
from typing import Any, Callable, Dict

from .base import Tool


# 支持的二元运算符
BINARY_OPERATORS: Dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


# 支持的一元运算符
UNARY_OPERATORS: Dict[type, Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def evaluate_expression(expression: str) -> int | float:
    """
    安全计算数学表达式。

    支持：
    1. 加法；
    2. 减法；
    3. 乘法；
    4. 除法；
    5. 整除；
    6. 取余；
    7. 乘方；
    8. 正负号；
    9. 括号。

    不支持：
    1. 变量；
    2. 函数调用；
    3. 属性访问；
    4. 字符串；
    5. 列表、字典等其他 Python 语法。
    """

    if not isinstance(expression, str):
        raise TypeError("表达式必须是字符串。")

    expression = expression.strip()

    if not expression:
        raise ValueError("表达式不能为空。")

    if len(expression) > 200:
        raise ValueError("表达式过长。")

    try:
        parsed_expression = ast.parse(
            expression,
            mode="eval",
        )
    except SyntaxError as error:
        raise ValueError("表达式语法错误。") from error

    result = _evaluate_node(parsed_expression.body)

    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("计算结果不是有限数值。")

    return result


def _evaluate_node(node: ast.AST) -> int | float:
    """
    递归计算 AST 节点。

    只处理允许的节点类型。
    """

    # Python 3.8 及以上版本中，
    # 数字通常会被解析成 ast.Constant。
    if isinstance(node, ast.Constant):
        value = node.value

        # bool 是 int 的子类，因此需要单独排除。
        if isinstance(value, bool):
            raise ValueError("不支持布尔值。")

        if not isinstance(value, (int, float)):
            raise ValueError("只支持数字。")

        return value

    # 处理二元运算，例如：
    # 1 + 2
    # 3 * 4
    # 10 / 2
    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)

        if operator_type not in BINARY_OPERATORS:
            raise ValueError(
                f"不支持的二元运算符：{operator_type.__name__}"
            )

        left_value = _evaluate_node(node.left)
        right_value = _evaluate_node(node.right)

        # 防止使用过大的指数进行计算。
        if isinstance(node.op, ast.Pow):
            if abs(right_value) > 100:
                raise ValueError("指数绝对值不能超过 100。")

        operation = BINARY_OPERATORS[operator_type]

        return operation(left_value, right_value)

    # 处理一元运算，例如：
    # -5
    # +8
    if isinstance(node, ast.UnaryOp):
        operator_type = type(node.op)

        if operator_type not in UNARY_OPERATORS:
            raise ValueError(
                f"不支持的一元运算符：{operator_type.__name__}"
            )

        operand_value = _evaluate_node(node.operand)
        operation = UNARY_OPERATORS[operator_type]

        return operation(operand_value)

    raise ValueError(
        f"表达式包含不允许的语法：{type(node).__name__}"
    )


class CalculatorTool(Tool):
    """
    安全计算器工具。
    """

    def __init__(self) -> None:
        super().__init__(
            name="calculator",
            description=(
                "计算数学表达式。"
                "支持加、减、乘、除、整除、取余、乘方和括号。"
                "参数格式：{'expression': '数学表达式'}。"
            ),
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行计算器工具。

        parameters 示例：

        {
            "expression": "(12 + 8) * 3"
        }
        """

        if not isinstance(parameters, dict):
            raise TypeError("parameters 必须是字典。")

        expression = parameters.get("expression")

        if expression is None:
            raise ValueError("缺少参数：expression")

        result = evaluate_expression(expression)

        return str(result)