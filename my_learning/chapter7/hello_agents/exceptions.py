class HelloAgentsError(Exception):
    """
    Hello-Agents 框架所有自定义异常的基类。
    """

    pass


class ConfigurationError(HelloAgentsError):
    """
    配置错误。

    例如：
    - API Key 缺失；
    - max_steps 不合法；
    - 配置值类型错误。
    """

    pass


class LLMError(HelloAgentsError):
    """
    大模型调用相关错误。
    """

    pass


class AgentError(HelloAgentsError):
    """
    Agent 相关异常的基类。
    """

    pass


class AgentExecutionError(AgentError):
    """
    Agent 执行过程发生错误。
    """

    pass


class PlanParseError(AgentError):
    """
    Plan-and-Solve 的计划解析失败。
    """

    pass


class ToolError(HelloAgentsError):
    """
    工具相关异常的基类。
    """

    pass


class ToolRegistrationError(ToolError):
    """
    工具注册失败。

    例如同名工具重复注册。
    """

    pass


class ToolNotFoundError(ToolError):
    """
    根据名称找不到工具。
    """

    pass


class ToolExecutionError(ToolError):
    """
    工具运行过程中发生错误。
    """

    pass


class ToolChainError(ToolError):
    """
    工具链构建或执行失败。
    """

    pass