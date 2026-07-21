import json
from datetime import datetime
from typing import Any

from memory.base import MemoryItem
from memory.manager import MemoryManager


class MemoryTool:
    """
    记忆工具。

    负责接收 JSON 格式的工具参数，
    再将操作转交给 MemoryManager。

    支持的操作：

    1. add：添加记忆
    2. get：根据 ID 获取记忆
    3. search：搜索记忆
    4. update：更新记忆
    5. forget：遗忘低重要性记忆
    6. consolidate：整合记忆
    7. stats：查看记忆统计
    8. clear：清空记忆
    """

    name = "MemoryTool"

    description = """
记忆管理工具。

输入必须是 JSON 字符串，并且必须包含 action 字段。

支持的 action：

1. add
添加一条记忆。

示例：
{
    "action": "add",
    "content": "用户正在学习 Chapter 8",
    "memory_type": "episodic",
    "importance": 0.8,
    "metadata": {
        "category": "learning_progress"
    }
}

2. search
搜索相关记忆。

示例：
{
    "action": "search",
    "query": "用户学习到哪一章了",
    "memory_types": ["episodic", "semantic"],
    "limit": 5
}

3. get
根据记忆 ID 获取记忆。

示例：
{
    "action": "get",
    "memory_id": "记忆ID"
}

4. update
更新已有记忆。

示例：
{
    "action": "update",
    "memory_id": "记忆ID",
    "content": "用户已经完成 Chapter 8",
    "importance": 0.9
}

5. forget
删除重要性低于阈值的记忆。

示例：
{
    "action": "forget",
    "threshold": 0.4,
    "memory_types": ["working"]
}

6. consolidate
将重要记忆从一种记忆类型整合到另一种类型。

示例：
{
    "action": "consolidate",
    "source_type": "working",
    "target_type": "episodic",
    "min_importance": 0.7
}

7. stats
查看各种记忆的数量。

示例：
{
    "action": "stats"
}

8. clear
清空指定类型或全部记忆。

示例：
{
    "action": "clear",
    "memory_type": "working"
}
""".strip()

    def __init__(
        self,
        manager: MemoryManager,
    ) -> None:
        """
        初始化记忆工具。

        manager:
            已经创建好的 MemoryManager。
        """

        if not isinstance(manager, MemoryManager):
            raise TypeError(
                "manager 必须是 MemoryManager 对象。"
            )

        self.manager = manager

    def run(
        self,
        tool_input: str,
    ) -> str:
        """
        接收 JSON 字符串并执行操作。

        这个方法以后可以直接注册到 ToolExecutor：

        func=memory_tool.run
        """

        try:
            if not isinstance(tool_input, str):
                raise TypeError(
                    "工具输入必须是 JSON 字符串。"
                )

            data = json.loads(tool_input)

            if not isinstance(data, dict):
                raise ValueError(
                    "JSON 最外层必须是对象。"
                )

            action = data.pop("action", None)

            return self.execute(
                action=action,
                **data,
            )

        except json.JSONDecodeError as error:
            return self._error_response(
                f"JSON 解析失败：{error}"
            )

        except Exception as error:
            return self._error_response(str(error))

    def execute(
        self,
        action: str | None,
        **kwargs: Any,
    ) -> str:
        """
        根据 action 将操作分发给对应方法。
        """

        if not isinstance(action, str):
            return self._error_response(
                "缺少有效的 action 字段。"
            )

        action = action.strip().lower()

        handlers = {
            "add": self._add,
            "get": self._get,
            "search": self._search,
            "update": self._update,
            "forget": self._forget,
            "consolidate": self._consolidate,
            "stats": self._stats,
            "clear": self._clear,
        }

        handler = handlers.get(action)

        if handler is None:
            supported_actions = ", ".join(
                handlers.keys()
            )

            return self._error_response(
                message=(
                    f"不支持的 action：{action}。"
                    f"支持的操作包括：{supported_actions}。"
                ),
                action=action,
            )

        try:
            result = handler(**kwargs)

            return self._success_response(
                action=action,
                result=result,
            )

        except Exception as error:
            return self._error_response(
                message=str(error),
                action=action,
            )

    def _add(
        self,
        content: str,
        memory_type: str = "working",
        importance: float = 0.5,
        metadata: dict | None = None,
    ) -> dict:
        """
        添加记忆。
        """

        if metadata is None:
            metadata = {}

        item = MemoryItem(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata,
        )

        self.manager.add(item)

        return self._item_to_dict(item)

    def _get(
        self,
        memory_id: str,
        memory_type: str | None = None,
    ) -> dict | None:
        """
        根据 ID 获取记忆。
        """

        item = self.manager.get(
            memory_id=memory_id,
            memory_type=memory_type,
        )

        if item is None:
            return None

        return self._item_to_dict(item)

    def _search(
        self,
        query: str,
        memory_types: list[str] | None = None,
        limit: int | None = 5,
        min_importance: float | None = None,
    ) -> dict:
        """
        搜索记忆。
        """

        results = self.manager.search(
            query=query,
            memory_types=memory_types,
            limit=limit,
            min_importance=min_importance,
        )

        return {
            "count": len(results),
            "items": [
                self._item_to_dict(item)
                for item in results
            ],
        }

    def _update(
        self,
        memory_id: str,
        content: str | None = None,
        importance: float | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """
        更新记忆。
        """

        updated_item = self.manager.update(
            memory_id=memory_id,
            content=content,
            importance=importance,
            metadata=metadata,
        )

        return self._item_to_dict(updated_item)

    def _forget(
        self,
        threshold: float,
        memory_types: list[str] | None = None,
    ) -> dict:
        """
        遗忘低重要性记忆。
        """

        forgotten_items = self.manager.forget(
            threshold=threshold,
            memory_types=memory_types,
        )

        return {
            "forgotten_count": len(
                forgotten_items
            ),
            "items": [
                self._item_to_dict(item)
                for item in forgotten_items
            ],
        }

    def _consolidate(
        self,
        source_type: str = "working",
        target_type: str = "episodic",
        min_importance: float = 0.7,
        limit: int | None = None,
        remove_from_source: bool = True,
    ) -> dict:
        """
        整合记忆。
        """

        consolidated_items = (
            self.manager.consolidate(
                source_type=source_type,
                target_type=target_type,
                min_importance=min_importance,
                limit=limit,
                remove_from_source=remove_from_source,
            )
        )

        return {
            "consolidated_count": len(
                consolidated_items
            ),
            "items": [
                self._item_to_dict(item)
                for item in consolidated_items
            ],
        }

    def _stats(self) -> dict:
        """
        获取记忆统计信息。
        """

        return self.manager.stats()

    def _clear(
        self,
        memory_type: str | None = None,
    ) -> dict:
        """
        清空记忆。
        """

        cleared_count = self.manager.clear(
            memory_type=memory_type,
        )

        return {
            "memory_type": (
                memory_type
                if memory_type is not None
                else "all"
            ),
            "cleared_count": cleared_count,
        }

    @staticmethod
    def _item_to_dict(
        item: MemoryItem,
    ) -> dict:
        """
        将 MemoryItem 转换为可以输出为 JSON 的字典。
        """

        created_at = item.created_at

        if isinstance(created_at, datetime):
            created_at = created_at.isoformat(
                timespec="seconds"
            )
        else:
            created_at = str(created_at)

        return {
            "id": item.id,
            "content": item.content,
            "memory_type": item.memory_type,
            "importance": item.importance,
            "metadata": item.metadata,
            "created_at": created_at,
        }

    @staticmethod
    def _success_response(
        action: str,
        result: Any,
    ) -> str:
        """
        构造成功结果。
        """

        response = {
            "success": True,
            "action": action,
            "result": result,
        }

        return json.dumps(
            response,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    @staticmethod
    def _error_response(
        message: str,
        action: str | None = None,
    ) -> str:
        """
        构造错误结果。
        """

        response = {
            "success": False,
            "error": message,
        }

        if action is not None:
            response["action"] = action

        return json.dumps(
            response,
            ensure_ascii=False,
            indent=2,
        )