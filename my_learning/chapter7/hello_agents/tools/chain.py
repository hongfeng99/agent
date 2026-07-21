from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .registry import ToolRegistry

from ..exceptions import (
    ToolChainError,
    ToolError,
)


# 参数构造函数的类型：
#
# 输入：
#     当前工具链上下文字典
#
# 返回：
#     当前工具需要的参数字典
ParameterBuilder = Callable[
    [Dict[str, Any]],
    Dict[str, Any],
]


@dataclass
class ToolChainStep:
    """
    工具链中的一个执行步骤。

    name:
        当前步骤的名称，例如“计算第一步表达式”。

    tool_name:
        要调用的工具名称，例如 calculator。

    parameter_builder:
        根据当前上下文，构造工具参数的函数。

    output_key:
        当前步骤执行结果保存到上下文时使用的键。
    """

    name: str
    tool_name: str
    parameter_builder: ParameterBuilder
    output_key: str


class ToolChain:
    """
    按照固定顺序执行多个工具的工具链。

    工具链中的后续步骤可以读取前面步骤的结果。
    """

    def __init__(
        self,
        name: str,
        tool_registry: ToolRegistry,
        description: str = "",
    ) -> None:
        if not isinstance(name, str):
            raise TypeError("工具链名称必须是字符串。")

        name = name.strip()

        if not name:
            raise ValueError("工具链名称不能为空。")

        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError(
                "tool_registry 必须是 ToolRegistry 对象。"
            )

        self.name = name
        self.description = description.strip()
        self.tool_registry = tool_registry

        # 按照添加顺序保存工具链步骤
        self._steps: List[ToolChainStep] = []

    def add_step(
        self,
        name: str,
        tool_name: str,
        parameter_builder: ParameterBuilder,
        output_key: Optional[str] = None,
    ) -> None:
        """
        向工具链末尾添加一个步骤。

        name:
            当前步骤的说明名称。

        tool_name:
            要调用的已注册工具名称。

        parameter_builder:
            根据上下文生成工具参数的函数。

        output_key:
            当前步骤结果在上下文中的保存名称。
            不传入时，自动生成 step_1_result 等名称。
        """

        if not isinstance(name, str):
            raise TypeError("步骤名称必须是字符串。")

        name = name.strip()

        if not name:
            raise ValueError("步骤名称不能为空。")

        if not isinstance(tool_name, str):
            raise TypeError("工具名称必须是字符串。")

        tool_name = tool_name.strip()

        if not tool_name:
            raise ValueError("工具名称不能为空。")

        if tool_name not in self.tool_registry:
            raise ValueError(
                f"工具尚未注册：{tool_name}"
            )

        if not callable(parameter_builder):
            raise TypeError(
                "parameter_builder 必须是可调用对象。"
            )

        if output_key is None:
            output_key = (
                f"step_{len(self._steps) + 1}_result"
            )

        if not isinstance(output_key, str):
            raise TypeError("output_key 必须是字符串。")

        output_key = output_key.strip()

        if not output_key:
            raise ValueError("output_key 不能为空。")

        existing_output_keys = {
            step.output_key
            for step in self._steps
        }

        if output_key in existing_output_keys:
            raise ValueError(
                f"结果键已经存在：{output_key}"
            )

        step = ToolChainStep(
            name=name,
            tool_name=tool_name,
            parameter_builder=parameter_builder,
            output_key=output_key,
        )

        self._steps.append(step)

    def execute(
        self,
        initial_context: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        按照添加顺序执行工具链中的所有步骤。

        initial_context:
            工具链开始执行时的初始数据。

        返回：
            包含初始数据和所有步骤结果的上下文字典。
        """

        if initial_context is None:
            context: Dict[str, Any] = {}
        else:
            if not isinstance(initial_context, dict):
                raise TypeError(
                    "initial_context 必须是字典。"
                )

            # 复制一份，避免直接修改调用者传入的字典
            context = initial_context.copy()

        if not self._steps:
            raise ValueError(
                f"工具链 {self.name} 中没有任何步骤。"
            )

        execution_trace = []

        for step_number, step in enumerate(
            self._steps,
            start=1,
        ):
            try:
                parameters = step.parameter_builder(
                    context
                )
            except Exception as error:
                raise ToolChainError(
                    f"工具链 {self.name} 的第 "
                    f"{step_number} 步参数构造失败："
                    f"{type(error).__name__}: {error}"
                ) from error

            if not isinstance(parameters, dict):
                raise TypeError(
                    f"工具链第 {step_number} 步的"
                    "参数构造函数必须返回字典。"
                )

            try:
                result = self.tool_registry.execute_or_raise(
                    name=step.tool_name,
                    parameters=parameters,
                )

            except ToolError as error:
                raise ToolChainError(
                    f"工具链 {self.name} 的第 "
                    f"{step_number} 步执行失败：{error}"
                ) from error

            # 将当前步骤结果写入上下文，
            # 后续步骤即可通过 context 读取。
            context[step.output_key] = result

            execution_trace.append(
                {
                    "step_number": step_number,
                    "step_name": step.name,
                    "tool_name": step.tool_name,
                    "parameters": parameters,
                    "output_key": step.output_key,
                    "result": result,
                }
            )

        # 执行轨迹也放入最终上下文中，
        # 方便后续查看和调试。
        context["_execution_trace"] = execution_trace

        return context

    def list_steps(self) -> List[ToolChainStep]:
        """
        返回工具链中的全部步骤。
        """

        return self._steps.copy()

    def __len__(self) -> int:
        """
        返回工具链中的步骤数量。
        """

        return len(self._steps)
    


class ToolChainManager:
    """
    工具链管理器。

    负责：

    1. 注册工具链；
    2. 根据名称查找工具链；
    3. 执行指定工具链；
    4. 删除工具链；
    5. 列出所有工具链。
    """

    def __init__(self) -> None:
        self._chains: Dict[str, ToolChain] = {}

    def register(
        self,
        chain: ToolChain,
    ) -> None:
        """
        注册一个工具链。
        """

        if not isinstance(chain, ToolChain):
            raise TypeError(
                "注册对象必须是 ToolChain。"
            )

        if chain.name in self._chains:
            raise ValueError(
                f"工具链已经存在：{chain.name}"
            )

        self._chains[chain.name] = chain

    def unregister(
        self,
        name: str,
    ) -> None:
        """
        根据名称删除工具链。
        """

        if name not in self._chains:
            raise KeyError(
                f"工具链不存在：{name}"
            )

        del self._chains[name]

    def get(
        self,
        name: str,
    ) -> Optional[ToolChain]:
        """
        根据名称获取工具链。
        """

        return self._chains.get(name)

    def execute(
        self,
        name: str,
        initial_context: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        执行指定名称的工具链。
        """

        chain = self.get(name)

        if chain is None:
            raise KeyError(
                f"工具链不存在：{name}"
            )

        return chain.execute(
            initial_context=initial_context,
        )

    def list_chains(
        self,
    ) -> List[ToolChain]:
        """
        返回所有已经注册的工具链。
        """

        return list(self._chains.values())

    def __len__(self) -> int:
        """
        返回已注册工具链数量。
        """

        return len(self._chains)

    def __contains__(
        self,
        name: str,
    ) -> bool:
        """
        支持：

        "calculation_chain" in manager
        """

        return name in self._chains