import ast
import operator
import os
from typing import Callable, Dict, Optional

from dotenv import load_dotenv
from tavily import TavilyClient


load_dotenv()


class ToolExecutor:
    """
    工具执行器。

    负责：
    1. 注册工具；
    2. 保存工具描述；
    3. 根据工具名称查找函数；
    4. 向大模型展示可用工具。
    """

    def __init__(self):
        # 工具名称 -> 工具信息
        self.tools: Dict[str, Dict[str, object]] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        func: Callable[[str], str],
    ) -> None:
        """
        注册一个工具。

        name:
            工具名称，例如 Calculator。

        description:
            工具的自然语言说明，后续会提供给大模型。

        func:
            真正由 Python 执行的函数。
        """

        if name in self.tools:
            print(f"警告：工具 {name} 已存在，将覆盖旧工具。")

        self.tools[name] = {
            "description": description,
            "func": func,
        }

        print(f"工具 {name} 注册成功。")

    def get_tool(self, name: str) -> Optional[Callable[[str], str]]:
        """
        根据名称获取工具函数。
        """

        tool_info = self.tools.get(name)

        if not tool_info:
            return None

        tool_function = tool_info.get("func")

        if callable(tool_function):
            return tool_function

        return None

    def get_available_tools(self) -> str:
        """
        将所有工具整理成适合放入提示词的文本。
        """

        if not self.tools:
            return "当前没有可用工具。"

        tool_descriptions = []

        for name, info in self.tools.items():
            description = info["description"]
            tool_descriptions.append(f"- {name}: {description}")

        return "\n".join(tool_descriptions)

    def execute(self, name: str, tool_input: str) -> str:
        """
        根据工具名称执行工具。

        这样 ReAct Agent 不需要自己重复编写
        “查找函数、判断函数是否存在、捕获异常”的逻辑。
        """

        tool_function = self.get_tool(name)

        if tool_function is None:
            available_names = ", ".join(self.tools.keys())

            return (
                f"工具执行失败：不存在名为 {name} 的工具。"
                f"当前可用工具：{available_names}"
            )

        try:
            return tool_function(tool_input)
        except Exception as error:
            return f"工具 {name} 执行失败：{error}"


# 支持的二元运算符
BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


# 支持的一元运算符
UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def evaluate_expression(node: ast.AST) -> float:
    """
    递归解析数学表达式的抽象语法树。

    只允许数字和指定数学运算，
    不允许执行普通 Python 代码。
    """

    # Python 3.8 以上的数字节点
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value

        raise ValueError("表达式中只能包含数字")

    # 二元运算，例如 1 + 2、3 * 4
    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)

        if operator_type not in BINARY_OPERATORS:
            raise ValueError("包含不支持的运算符")

        left_value = evaluate_expression(node.left)
        right_value = evaluate_expression(node.right)

        operation = BINARY_OPERATORS[operator_type]

        return operation(left_value, right_value)

    # 一元运算，例如 -5、+8
    if isinstance(node, ast.UnaryOp):
        operator_type = type(node.op)

        if operator_type not in UNARY_OPERATORS:
            raise ValueError("包含不支持的一元运算符")

        operand_value = evaluate_expression(node.operand)
        operation = UNARY_OPERATORS[operator_type]

        return operation(operand_value)

    raise ValueError("表达式中包含不允许的内容")


def calculator(expression: str) -> str:
    """
    计算数学表达式。

    示例：
    2 + 3 * 4
    (100 - 20) / 4
    2 ** 8
    """

    expression = expression.strip()

    if not expression:
        return "计算失败：没有提供数学表达式。"

    try:
        expression_tree = ast.parse(expression, mode="eval")

        result = evaluate_expression(expression_tree.body)

        return str(result)

    except ZeroDivisionError:
        return "计算失败：除数不能为 0。"

    except (SyntaxError, ValueError, TypeError) as error:
        return f"计算失败：{error}"

    except Exception as error:
        return f"计算失败：发生未知错误：{error}"


def tavily_search(query: str) -> str:
    """
    使用 Tavily 搜索互联网信息。

    参数：
        query：自然语言搜索问题。

    返回：
        整理后的前三条搜索结果。
    """

    query = query.strip()

    if not query:
        return "搜索失败：没有提供搜索内容。"

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return "搜索失败：没有配置 TAVILY_API_KEY。"

    try:
        client = TavilyClient(api_key=api_key)

        response = client.search(
            query=query,
            search_depth="basic",
            max_results=3,
            include_answer=False,
        )

        results = response.get("results", [])

        if not results:
            return "没有搜索到相关结果。"

        formatted_results = []

        for index, item in enumerate(results, start=1):
            title = item.get("title", "未命名结果")
            content = item.get("content", "没有摘要")
            url = item.get("url", "没有链接")

            formatted_results.append(
                f"{index}. {title}\n"
                f"摘要：{content}\n"
                f"来源：{url}"
            )

        return "\n\n".join(formatted_results)

    except Exception as error:
        return f"搜索失败：{error}"

def create_default_tool_executor() -> ToolExecutor:
    """
    创建并返回默认工具箱。

    当前包含：
    1. Calculator：数学计算；
    2. Search：互联网搜索。
    """

    tool_executor = ToolExecutor()

    calculator_description = (
        "数学计算工具。"
        "当任务需要进行加、减、乘、除、取余、整除或乘方运算时使用。"
        "输入必须是数学表达式，例如：(125 * 8) + 50。"
    )

    tool_executor.register_tool(
        name="Calculator",
        description=calculator_description,
        func=calculator,
    )

    search_description = (
        "互联网搜索工具。"
        "当问题需要查询外部事实、最新信息、人物资料、"
        "地点数据或其他无法仅靠当前上下文确定的信息时使用。"
        "输入应当是清晰、完整的搜索关键词或问题。"
    )

    tool_executor.register_tool(
        name="Search",
        description=search_description,
        func=tavily_search,
    )

    return tool_executor


def main():
    """
    独立测试工具注册、查找和执行是否正常。
    """

    tool_executor = create_default_tool_executor()

    print("\n--- 当前可用工具 ---")
    print(tool_executor.get_available_tools())

    print("\n--- 测试一：正常计算 ---")
    observation_1 = tool_executor.execute(
        name="Calculator",
        tool_input="(125 * 8) + 50",
    )
    print(f"Observation: {observation_1}")

    print("\n--- 测试二：除数为零 ---")
    observation_2 = tool_executor.execute(
        name="Calculator",
        tool_input="100 / 0",
    )
    print(f"Observation: {observation_2}")

    print("\n--- 测试三：不存在的工具 ---")
    observation_3 = tool_executor.execute(
        name="Search",
        tool_input="今天东京的天气",
    )
    print(f"Observation: {observation_3}")

    print("\n--- 测试四：不允许的 Python 代码 ---")
    observation_4 = tool_executor.execute(
        name="Calculator",
        tool_input="print('hello')",
    )
    print(f"Observation: {observation_4}")

    print("\n--- 测试八：Tavily 搜索 ---")
    observation_8 = tool_executor.execute(
        name="Search",
        tool_input="东京晴空塔的官方高度是多少米",
    )
    print(f"Observation:\n{observation_8}")


if __name__ == "__main__":
    main()