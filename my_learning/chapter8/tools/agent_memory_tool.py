import json
from typing import Any, Dict

from hello_agents.tools.base import Tool

from tools.memory_tool import MemoryTool


class AgentMemoryTool(Tool):
    """
    将 Chapter 8 的 MemoryTool
    适配成 Chapter 7 工具系统能够注册的 Tool。
    """

    def __init__(self, memory_tool: MemoryTool) -> None:
        super().__init__(
            name="memory",
            description="""
记忆管理工具。

当需要保存、搜索、更新或管理用户记忆时使用该工具。

parameters 必须是一个字典，其中 action 表示具体操作。

支持的 action：

1. add：添加记忆
示例：
{
    "action": "add",
    "content": "用户已经完成 Chapter 8 的基础记忆系统",
    "memory_type": "episodic",
    "importance": 0.9
}

2. search：搜索记忆
示例：
{
    "action": "search",
    "query": "Chapter 8 学习进度",
    "memory_types": ["working", "episodic", "semantic"],
    "limit": 5
}

3. stats：查看记忆统计
示例：
{
    "action": "stats"
}

4. consolidate：整合记忆
示例：
{
    "action": "consolidate",
    "source_type": "working",
    "target_type": "episodic",
    "min_importance": 0.7
}
""".strip(),
        )

        if not isinstance(memory_tool, MemoryTool):
            raise TypeError(
                "memory_tool 必须是 MemoryTool 对象。"
            )

        self.memory_tool = memory_tool

    def run(
        self,
        parameters: Dict[str, Any],
    ) -> str:
        """
        接收 Chapter 7 ToolRegistry 传入的字典，
        转换为原 MemoryTool 所需的 JSON 字符串。
        """

        if not isinstance(parameters, dict):
            raise TypeError(
                "parameters 必须是字典。"
            )

        tool_input = json.dumps(
            parameters,
            ensure_ascii=False,
        )

        return self.memory_tool.run(tool_input)