from datetime import datetime
from typing import Any

from context import ContextBuilder, ContextPacket
from tools import NoteTool


class NoteContextAdapter:
    """
    NoteTool 与 ContextBuilder 之间的适配器。

    负责：

    1. 从 NoteTool 检索相关笔记；
    2. 补全 list 返回的笔记正文；
    3. 将笔记转换为 ContextPacket；
    4. 把笔记注入 ContextBuilder。
    """

    RELEVANCE_BY_TYPE = {
        "blocker": 0.90,
        "action": 0.80,
        "task_state": 0.75,
        "conclusion": 0.70,
        "reference": 0.65,
        "general": 0.60,
    }

    def __init__(
        self,
        note_tool: NoteTool,
        context_builder: ContextBuilder,
    ) -> None:
        self.note_tool = note_tool
        self.context_builder = context_builder

    def _hydrate_listed_note(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        为 list 操作返回的笔记元数据补充正文。

        NoteTool.list() 只返回索引元数据，不包含正文，
        因此需要再调用 read()。
        """

        note_id = (
            metadata.get("note_id")
            or metadata.get("id")
        )

        if not note_id:
            return None

        try:
            note = self.note_tool.run({
                "action": "read",
                "note_id": note_id,
            })
        except (
            ValueError,
            FileNotFoundError,
            OSError,
        ) as error:
            print(
                "[WARNING] "
                f"读取笔记 {note_id} 失败：{error}"
            )
            return None

        note_metadata = note.get(
            "metadata",
            {},
        )

        return {
            "note_id": note_id,
            "title": note_metadata.get(
                "title",
                metadata.get("title", "未命名笔记"),
            ),
            "type": note_metadata.get(
                "type",
                metadata.get("type", "general"),
            ),
            "tags": note_metadata.get(
                "tags",
                metadata.get("tags", []),
            ),
            "content": note.get(
                "content",
                "",
            ),
            "updated_at": note_metadata.get(
                "updated_at",
                metadata.get(
                    "updated_at",
                    datetime.now().isoformat(),
                ),
            ),
        }

    def retrieve_relevant_notes(
        self,
        query: str,
        limit: int = 3,
        blocker_limit: int = 1,
    ) -> list[dict[str, Any]]:
        """
        检索需要注入上下文的笔记。

        处理流程：

        1. 主动读取少量 blocker；
        2. 根据用户问题进行关键词搜索；
        3. 合并并按笔记 ID 去重；
        4. 按笔记类型优先级和更新时间排序；
        5. 限制最终数量。
        """

        if not isinstance(query, str):
            raise TypeError(
                "query 必须是字符串。"
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "query 不能为空。"
            )

        if limit <= 0:
            raise ValueError(
                "limit 必须大于 0。"
            )

        if blocker_limit < 0:
            raise ValueError(
                "blocker_limit 不能小于 0。"
            )

        notes: list[dict[str, Any]] = []

        # 1. 优先读取 blocker。
        if blocker_limit > 0:
            blocker_metadata = self.note_tool.run({
                "action": "list",
                "note_type": "blocker",
                "limit": blocker_limit,
            })

            for metadata in blocker_metadata:
                hydrated_note = (
                    self._hydrate_listed_note(
                        metadata
                    )
                )

                if hydrated_note is not None:
                    notes.append(hydrated_note)

        # 2. 搜索与当前问题相关的笔记。
        search_results = self.note_tool.run({
            "action": "search",
            "query": query,
            "limit": limit,
        })

        notes.extend(search_results)

        # 3. 按笔记 ID 去重。
        unique_notes: dict[
            str,
            dict[str, Any],
        ] = {}

        for note in notes:
            note_id = (
                note.get("note_id")
                or note.get("id")
            )

            if not note_id:
                continue

            unique_notes[note_id] = {
                **note,
                "note_id": note_id,
            }

        result = list(
            unique_notes.values()
        )

        # 4. 按笔记类型优先级和更新时间排序。
        result.sort(
            key=lambda note: (
                self.RELEVANCE_BY_TYPE.get(
                    note.get("type", "general"),
                    0.60,
                ),
                note.get("updated_at", ""),
            ),
            reverse=True,
        )

        return result[:limit]

    def notes_to_packets(
        self,
        notes: list[dict[str, Any]],
    ) -> list[ContextPacket]:
        """
        将笔记转换为 ContextPacket。
        """

        packets: list[ContextPacket] = []

        for note in notes:
            note_id = (
                note.get("note_id")
                or note.get("id")
            )

            title = note.get(
                "title",
                "未命名笔记",
            )

            note_type = note.get(
                "type",
                "general",
            )

            body = note.get(
                "content",
                "",
            )

            content = (
                f"[笔记：{title}]\n"
                f"类型：{note_type}\n\n"
                f"{body}"
            )

            updated_at = note.get(
                "updated_at",
                "",
            )

            try:
                timestamp = datetime.fromisoformat(
                    str(updated_at)
                )
            except (
                TypeError,
                ValueError,
            ):
                timestamp = datetime.now()

            relevance_score = (
                self.RELEVANCE_BY_TYPE.get(
                    note_type,
                    0.60,
                )
            )

            packets.append(
                ContextPacket(
                    content=content,
                    timestamp=timestamp,
                    token_count=(
                        self.context_builder
                        ._count_tokens(content)
                    ),
                    relevance_score=(
                        relevance_score
                    ),
                    metadata={
                        "type": "note",
                        "note_type": note_type,
                        "note_id": note_id,
                        "source": "note_tool",
                    },
                )
            )

        return packets

    def build_context(
        self,
        user_query: str,
        conversation_history: (
            list[Any] | None
        ) = None,
        system_instructions: str | None = None,
        limit: int = 3,
    ) -> str:
        """
        检索笔记并构建最终上下文。
        """

        notes = self.retrieve_relevant_notes(
            query=user_query,
            limit=limit,
        )

        note_packets = self.notes_to_packets(
            notes
        )

        return self.context_builder.build(
            user_query=user_query,
            conversation_history=(
                conversation_history
            ),
            system_instructions=(
                system_instructions
            ),
            custom_packets=note_packets,
        )