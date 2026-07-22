import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class NoteTool:
    """
    结构化笔记工具。

    使用：

    1. Markdown 文件保存笔记正文；
    2. YAML 前置元数据保存标题、类型、标签和时间；
    3. notes_index.json 保存笔记索引。

    当前版本支持：

    - create：创建笔记；
    - read：读取笔记；
    - list：列出笔记。
    """

    ALLOWED_NOTE_TYPES = {
        "task_state",
        "conclusion",
        "blocker",
        "action",
        "reference",
        "general",
    }

    def __init__(
        self,
        workspace: str | Path,
    ) -> None:
        """
        初始化 NoteTool。

        workspace:
            笔记文件保存目录。
        """

        self.workspace = Path(workspace).resolve()

        # 如果目录不存在，就自动创建。
        self.workspace.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.index_path = (
            self.workspace / "notes_index.json"
        )

        self.index = self._load_index()



    def _load_index(
        self,
    ) -> dict[str, dict[str, Any]]:
        """
        加载笔记索引。

        如果索引文件不存在，则创建空索引。
        """

        if not self.index_path.exists():
            empty_index: dict[
                str,
                dict[str, Any],
            ] = {}

            self.index_path.write_text(
                json.dumps(
                    empty_index,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            return empty_index

        raw_text = self.index_path.read_text(
            encoding="utf-8"
        ).strip()

        if not raw_text:
            return {}

        try:
            loaded_index = json.loads(raw_text)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"笔记索引格式错误：{self.index_path}"
            ) from error

        if not isinstance(loaded_index, dict):
            raise ValueError(
                "笔记索引的根对象必须是字典。"
            )

        return loaded_index

    def _save_index(self) -> None:
        """
        将当前笔记索引保存到 JSON 文件。
        """

        self.index_path.write_text(
            json.dumps(
                self.index,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )



    def _build_markdown(
        self,
        metadata: dict[str, Any],
        content: str,
    ) -> str:
        """
        将 YAML 元数据和 Markdown 正文组合起来。
        """

        yaml_header = yaml.safe_dump(
            metadata,
            allow_unicode=True,
            sort_keys=False,
        )

        return (
            "---\n"
            f"{yaml_header}"
            "---\n\n"
            f"{content.strip()}\n"
        )

    def _parse_markdown(
        self,
        raw_content: str,
    ) -> tuple[dict[str, Any], str]:
        """
        解析带有 YAML 前置元数据的 Markdown 文件。
        """

        if not raw_content.startswith("---\n"):
            return {}, raw_content.strip()

        remaining_content = raw_content[4:]

        try:
            yaml_text, body = remaining_content.split(
                "\n---\n",
                maxsplit=1,
            )
        except ValueError:
            return {}, raw_content.strip()

        metadata = yaml.safe_load(yaml_text) or {}

        if not isinstance(metadata, dict):
            raise ValueError(
                "Markdown 中的 YAML 元数据必须是字典。"
            )

        return metadata, body.strip()
    



    def _create_note(
        self,
        title: str,
        content: str,
        note_type: str = "general",
        tags: list[str] | None = None,
    ) -> str:
        """
        创建一条新笔记，并返回笔记 ID。
        """

        if not isinstance(title, str):
            raise TypeError("title 必须是字符串。")

        if not title.strip():
            raise ValueError("title 不能为空。")

        if not isinstance(content, str):
            raise TypeError("content 必须是字符串。")

        if not content.strip():
            raise ValueError("content 不能为空。")

        if note_type not in self.ALLOWED_NOTE_TYPES:
            allowed_text = ", ".join(
                sorted(self.ALLOWED_NOTE_TYPES)
            )

            raise ValueError(
                f"不支持的笔记类型：{note_type}。"
                f"允许的类型：{allowed_text}"
            )

        if tags is None:
            tags = []

        if not isinstance(tags, list):
            raise TypeError("tags 必须是列表。")

        if not all(
            isinstance(tag, str)
            for tag in tags
        ):
            raise TypeError(
                "tags 中的每个元素都必须是字符串。"
            )

        now = datetime.now()

        # 使用微秒保证 ID 基本不会重复。
        note_id = (
            "note_"
            + now.strftime(
                "%Y%m%d_%H%M%S_%f"
            )
        )

        metadata = {
            "id": note_id,
            "title": title.strip(),
            "type": note_type,
            "tags": tags,
            "created_at": now.isoformat(
                timespec="seconds"
            ),
            "updated_at": now.isoformat(
                timespec="seconds"
            ),
        }

        markdown_text = self._build_markdown(
            metadata=metadata,
            content=content,
        )

        file_path = (
            self.workspace / f"{note_id}.md"
        )

        file_path.write_text(
            markdown_text,
            encoding="utf-8",
        )

        # file_path 只写入索引，
        # 不写入 Markdown 的 YAML 元数据。
        index_metadata = {
            **metadata,
            "file_path": str(file_path),
        }

        self.index[note_id] = index_metadata
        self._save_index()

        return note_id
    


    def _read_note(
        self,
        note_id: str,
    ) -> dict[str, Any]:
        """
        根据笔记 ID 读取笔记。
        """

        if note_id not in self.index:
            raise ValueError(
                f"笔记不存在：{note_id}"
            )

        file_path = Path(
            self.index[note_id]["file_path"]
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"笔记文件不存在：{file_path}"
            )

        raw_content = file_path.read_text(
            encoding="utf-8"
        )

        metadata, content = (
            self._parse_markdown(raw_content)
        )

        return {
            "metadata": metadata,
            "content": content,
        }
    

    def _update_note(
        self,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        note_type: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """
        更新已有笔记。

        没有传入的字段保持原值不变。
        """

        if not isinstance(note_id, str):
            raise TypeError("note_id 必须是字符串。")

        if note_id not in self.index:
            raise ValueError(
                f"笔记不存在：{note_id}"
            )

        if title is not None:
            if not isinstance(title, str):
                raise TypeError(
                    "title 必须是字符串。"
                )

            if not title.strip():
                raise ValueError(
                    "title 不能为空。"
                )

        if content is not None:
            if not isinstance(content, str):
                raise TypeError(
                    "content 必须是字符串。"
                )

            if not content.strip():
                raise ValueError(
                    "content 不能为空。"
                )

        if note_type is not None:
            if note_type not in self.ALLOWED_NOTE_TYPES:
                raise ValueError(
                    f"不支持的笔记类型：{note_type}"
                )

        if tags is not None:
            if not isinstance(tags, list):
                raise TypeError(
                    "tags 必须是列表。"
                )

            if not all(
                isinstance(tag, str)
                for tag in tags
            ):
                raise TypeError(
                    "tags 中的每个元素"
                    "都必须是字符串。"
                )

        # 1. 读取原笔记。
        note = self._read_note(note_id)

        metadata = dict(
            note["metadata"]
        )

        old_content = note["content"]

        # 2. 更新用户传入的字段。
        if title is not None:
            metadata["title"] = title.strip()

        if content is not None:
            old_content = content.strip()

        if note_type is not None:
            metadata["type"] = note_type

        if tags is not None:
            metadata["tags"] = tags

        # 3. 更新修改时间。
        metadata["updated_at"] = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        # 文件路径保存在索引中，
        # 而不是 Markdown 的 YAML 元数据中。
        file_path = Path(
            self.index[note_id]["file_path"]
        )

        markdown_text = self._build_markdown(
            metadata=metadata,
            content=old_content,
        )

        # 4. 重新写入 Markdown 文件。
        file_path.write_text(
            markdown_text,
            encoding="utf-8",
        )

        # 5. 同步更新索引。
        self.index[note_id] = {
            **metadata,
            "file_path": str(file_path),
        }

        self._save_index()

        return (
            f"笔记已更新："
            f"{metadata['title']}"
        )



    def _list_notes(
        self,
        note_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        列出笔记元数据。

        可以按照笔记类型和标签过滤，
        最终按照更新时间倒序排列。
        """

        if limit <= 0:
            raise ValueError(
                "limit 必须大于 0。"
            )

        if (
            note_type is not None
            and note_type
            not in self.ALLOWED_NOTE_TYPES
        ):
            raise ValueError(
                f"不支持的笔记类型：{note_type}"
            )

        if tags is not None:
            if not isinstance(tags, list):
                raise TypeError(
                    "tags 必须是列表。"
                )

            if not all(
                isinstance(tag, str)
                for tag in tags
            ):
                raise TypeError(
                    "tags 中的元素必须是字符串。"
                )

        results: list[dict[str, Any]] = []

        for metadata in self.index.values():
            if (
                note_type is not None
                and metadata.get("type")
                != note_type
            ):
                continue

            if tags:
                note_tags = set(
                    metadata.get("tags", [])
                )

                requested_tags = set(tags)

                # 至少有一个共同标签时保留。
                if not note_tags.intersection(
                    requested_tags
                ):
                    continue

            results.append(
                dict(metadata)
            )

        results.sort(
            key=lambda item: item.get(
                "updated_at",
                "",
            ),
            reverse=True,
        )

        return results[:limit]
    

    def run(
        self,
        parameters: dict[str, Any],
    ) -> Any:
        """
        根据 action 执行笔记操作。

        支持：

        - create
        - read
        - update
        - search
        - list
        - summary
        - delete
        """

        if not isinstance(parameters, dict):
            raise TypeError(
                "parameters 必须是字典。"
            )

        action = parameters.get("action")

        if not isinstance(action, str):
            raise ValueError(
                "必须提供字符串类型的 action。"
            )

        if action == "create":
            return self._create_note(
                title=parameters.get(
                    "title",
                    "",
                ),
                content=parameters.get(
                    "content",
                    "",
                ),
                note_type=parameters.get(
                    "note_type",
                    "general",
                ),
                tags=parameters.get(
                    "tags",
                ),
            )

        if action == "read":
            return self._read_note(
                note_id=parameters.get(
                    "note_id",
                    "",
                ),
            )

        if action == "update":
            return self._update_note(
                note_id=parameters.get(
                    "note_id",
                    "",
                ),
                title=parameters.get(
                    "title",
                ),
                content=parameters.get(
                    "content",
                ),
                note_type=parameters.get(
                    "note_type",
                ),
                tags=parameters.get(
                    "tags",
                ),
            )

        if action == "search":
            return self._search_notes(
                query=parameters.get(
                    "query",
                    "",
                ),
                limit=parameters.get(
                    "limit",
                    10,
                ),
                note_type=parameters.get(
                    "note_type",
                ),
                tags=parameters.get(
                    "tags",
                ),
            )

        if action == "list":
            return self._list_notes(
                note_type=parameters.get(
                    "note_type",
                ),
                tags=parameters.get(
                    "tags",
                ),
                limit=parameters.get(
                    "limit",
                    20,
                ),
            )

        if action == "summary":
            return self._summary()

        if action == "delete":
            return self._delete_note(
                note_id=parameters.get(
                    "note_id",
                    "",
                ),
            )

        supported_actions = (
            "create、read、update、search、"
            "list、summary、delete"
        )

        raise ValueError(
            f"不支持的 action：{action}。"
            f"当前支持：{supported_actions}。"
        )



    def _search_notes(
        self,
        query: str,
        limit: int = 10,
        note_type: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        根据关键词搜索笔记。

        搜索范围：

        1. 标题；
        2. Markdown 正文。

        还可以按照类型和标签过滤。
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

        if (
            note_type is not None
            and note_type
            not in self.ALLOWED_NOTE_TYPES
        ):
            raise ValueError(
                f"不支持的笔记类型：{note_type}"
            )

        if tags is not None:
            if not isinstance(tags, list):
                raise TypeError(
                    "tags 必须是列表。"
                )

            if not all(
                isinstance(tag, str)
                for tag in tags
            ):
                raise TypeError(
                    "tags 中的元素必须是字符串。"
                )

        query_lower = query.lower()

        results: list[dict[str, Any]] = []

        for note_id, metadata in self.index.items():
            # 1. 按类型过滤。
            if (
                note_type is not None
                and metadata.get("type")
                != note_type
            ):
                continue

            # 2. 按标签过滤。
            if tags:
                note_tags = set(
                    metadata.get("tags", [])
                )

                requested_tags = set(tags)

                if not note_tags.intersection(
                    requested_tags
                ):
                    continue

            # 3. 读取正文并搜索。
            try:
                note = self._read_note(note_id)
            except (
                ValueError,
                FileNotFoundError,
                OSError,
            ) as error:
                print(
                    "[WARNING] "
                    f"读取笔记 {note_id} 失败："
                    f"{error}"
                )

                continue

            title = metadata.get(
                "title",
                "",
            )

            content = note.get(
                "content",
                "",
            )

            title_matched = (
                query_lower in title.lower()
            )

            content_matched = (
                query_lower in content.lower()
            )

            if not (
                title_matched
                or content_matched
            ):
                continue

            results.append({
                "note_id": note_id,
                "title": title,
                "type": metadata.get(
                    "type",
                    "general",
                ),
                "tags": metadata.get(
                    "tags",
                    [],
                ),
                "content": content,
                "updated_at": metadata.get(
                    "updated_at",
                    "",
                ),
            })

        # 最近更新的笔记排在前面。
        results.sort(
            key=lambda item: item.get(
                "updated_at",
                "",
            ),
            reverse=True,
        )

        return results[:limit]
    




    def _summary(
        self,
    ) -> dict[str, Any]:
        """
        生成当前笔记库的统计摘要。

        返回：

        1. 笔记总数；
        2. 各类型笔记数量；
        3. 最近更新的 5 条笔记。
        """

        total_notes = len(self.index)

        type_distribution: dict[str, int] = {}

        for metadata in self.index.values():
            note_type = metadata.get(
                "type",
                "general",
            )

            type_distribution[note_type] = (
                type_distribution.get(
                    note_type,
                    0,
                )
                + 1
            )

        recent_notes = sorted(
            self.index.values(),
            key=lambda item: item.get(
                "updated_at",
                "",
            ),
            reverse=True,
        )[:5]

        return {
            "total_notes": total_notes,
            "type_distribution": (
                type_distribution
            ),
            "recent_notes": [
                {
                    "id": note.get("id"),
                    "title": note.get(
                        "title",
                        "",
                    ),
                    "type": note.get(
                        "type",
                        "general",
                    ),
                    "updated_at": note.get(
                        "updated_at",
                        "",
                    ),
                }
                for note in recent_notes
            ],
        }
    



    def _delete_note(
        self,
        note_id: str,
    ) -> str:
        """
        删除笔记文件及其索引。
        """

        if not isinstance(note_id, str):
            raise TypeError(
                "note_id 必须是字符串。"
            )

        if note_id not in self.index:
            raise ValueError(
                f"笔记不存在：{note_id}"
            )

        metadata = self.index[note_id]

        title = metadata.get(
            "title",
            note_id,
        )

        file_path = Path(
            metadata["file_path"]
        )

        # 1. 删除 Markdown 文件。
        if file_path.exists():
            file_path.unlink()

        # 2. 删除索引中的记录。
        del self.index[note_id]

        # 3. 保存索引。
        self._save_index()

        return f"笔记已删除：{title}"