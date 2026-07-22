from datetime import datetime
from pathlib import Path
from typing import Any


class TerminalTool:
    """
    安全的只读文件系统工具。

    当前支持：

    - pwd：查看当前目录；
    - list_files：列出目录内容；
    - tree：查看目录树；
    - read_file：读取文本文件；
    - search_text：在文本文件中搜索关键词；
    - file_info：查看文件或目录信息；
    - change_dir：切换当前目录。

    安全限制：

    1. 只能访问 workspace 及其子目录；
    2. 禁止读取敏感文件；
    3. 只允许读取常见文本文件；
    4. 限制单个文件大小；
    5. 限制单次返回内容长度；
    6. 不执行任意 Shell 命令。
    """

    ALLOWED_TEXT_EXTENSIONS = {
        ".py",
        ".txt",
        ".md",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".csv",
        ".tsv",
        ".html",
        ".css",
        ".js",
        ".ts",
        ".xml",
        ".sql",
        ".log",
    }

    ALLOWED_SPECIAL_FILENAMES = {
        "README",
        "LICENSE",
        "Dockerfile",
        ".gitignore",
        ".dockerignore",
    }

    SENSITIVE_FILENAMES = {
        ".env",
        "id_rsa",
        "id_ed25519",
        "credentials.json",
        "secrets.json",
    }

    SENSITIVE_EXTENSIONS = {
        ".pem",
        ".key",
        ".p12",
        ".pfx",
    }

    IGNORED_DIRECTORIES = {
        ".git",
        ".idea",
        ".vscode",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
    }

    SUPPORTED_ACTIONS = {
        "pwd",
        "list_files",
        "tree",
        "read_file",
        "search_text",
        "file_info",
        "change_dir",
    }

    def __init__(
        self,
        workspace: str | Path,
        max_output_chars: int = 20_000,
        max_file_size: int = 1_000_000,
    ) -> None:
        """
        初始化 TerminalTool。

        workspace:
            允许访问的根目录。

        max_output_chars:
            单次操作最多返回多少个字符。

        max_file_size:
            单个可读取文件的最大字节数。
        """

        if max_output_chars <= 0:
            raise ValueError(
                "max_output_chars 必须大于 0。"
            )

        if max_file_size <= 0:
            raise ValueError(
                "max_file_size 必须大于 0。"
            )

        self.workspace = Path(workspace).resolve()

        if not self.workspace.exists():
            raise FileNotFoundError(
                f"工作目录不存在：{self.workspace}"
            )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"workspace 不是目录：{self.workspace}"
            )

        self.current_dir = self.workspace
        self.max_output_chars = max_output_chars
        self.max_file_size = max_file_size




    def _resolve_path(
        self,
        path: str | Path = ".",
    ) -> Path:
        """
        解析路径，并确保路径位于 workspace 内。
        """

        if not isinstance(path, (str, Path)):
            raise TypeError(
                "path 必须是字符串或 Path。"
            )

        path_object = Path(path)

        if path_object.is_absolute():
            resolved_path = path_object.resolve()
        else:
            resolved_path = (
                self.current_dir / path_object
            ).resolve()

        try:
            resolved_path.relative_to(
                self.workspace
            )
        except ValueError as error:
            raise PermissionError(
                "不允许访问工作目录外的路径："
                f"{resolved_path}"
            ) from error

        return resolved_path
    

    def _truncate_output(
        self,
        output: str,
    ) -> str:
        """
        将工具输出限制在 max_output_chars 以内。
        """

        if not isinstance(output, str):
            raise TypeError(
                "output 必须是字符串。"
            )

        if len(output) <= self.max_output_chars:
            return output

        marker = (
            "\n\n[输出已截断，"
            f"最大允许 {self.max_output_chars} 个字符]"
        )

        available_chars = max(
            0,
            self.max_output_chars - len(marker),
        )

        return output[:available_chars] + marker



    def _is_sensitive_file(
        self,
        file_path: Path,
    ) -> bool:
        """
        判断文件是否属于敏感文件。
        """

        file_name = file_path.name.lower()
        suffix = file_path.suffix.lower()

        if file_name in self.SENSITIVE_FILENAMES:
            return True

        # 拦截 .env、.env.local、.env.example 等。
        if file_name.startswith(".env"):
            return True

        if suffix in self.SENSITIVE_EXTENSIONS:
            return True

        return False

    def _is_allowed_text_file(
        self,
        file_path: Path,
    ) -> bool:
        """
        判断文件是否属于允许读取的文本文件。
        """

        if file_path.name in self.ALLOWED_SPECIAL_FILENAMES:
            return True

        return (
            file_path.suffix.lower()
            in self.ALLOWED_TEXT_EXTENSIONS
        )

    def _validate_readable_file(
        self,
        file_path: Path,
    ) -> None:
        """
        检查文件是否可以安全读取。
        """

        if not file_path.exists():
            raise FileNotFoundError(
                f"文件不存在：{file_path}"
            )

        if not file_path.is_file():
            raise IsADirectoryError(
                f"目标不是文件：{file_path}"
            )

        if self._is_sensitive_file(file_path):
            raise PermissionError(
                f"禁止读取敏感文件：{file_path.name}"
            )

        if not self._is_allowed_text_file(file_path):
            raise PermissionError(
                "当前仅允许读取文本文件："
                f"{file_path.name}"
            )

        file_size = file_path.stat().st_size

        if file_size > self.max_file_size:
            raise ValueError(
                f"文件过大：{file_size} 字节，"
                f"最大允许 {self.max_file_size} 字节。"
            )
        


    def _pwd(self) -> str:
        """
        返回当前目录。
        """

        relative_path = self.current_dir.relative_to(
            self.workspace
        )

        display_path = (
            "."
            if str(relative_path) == "."
            else relative_path.as_posix()
        )

        return (
            f"工作目录：{self.workspace}\n"
            f"当前目录：{display_path}"
        )
    


    def _list_files(
        self,
        path: str | Path = ".",
        show_hidden: bool = False,
    ) -> str:
        """
        列出指定目录中的文件和子目录。
        """

        target_dir = self._resolve_path(path)

        if not target_dir.exists():
            raise FileNotFoundError(
                f"目录不存在：{target_dir}"
            )

        if not target_dir.is_dir():
            raise NotADirectoryError(
                f"目标不是目录：{target_dir}"
            )

        entries = []

        for entry in target_dir.iterdir():
            if (
                not show_hidden
                and entry.name.startswith(".")
            ):
                continue

            entries.append(entry)

        entries.sort(
            key=lambda entry: (
                not entry.is_dir(),
                entry.name.lower(),
            )
        )

        if not entries:
            return "目录为空。"

        lines: list[str] = []

        for entry in entries:
            if entry.is_dir():
                lines.append(
                    f"[DIR]  {entry.name}/"
                )
            else:
                size = entry.stat().st_size
                lines.append(
                    f"[FILE] {entry.name} "
                    f"({size} bytes)"
                )

        return self._truncate_output(
            "\n".join(lines)
        )
    


    def _tree(
        self,
        path: str | Path = ".",
        max_depth: int = 3,
    ) -> str:
        """
        生成简单目录树。
        """

        if max_depth < 0:
            raise ValueError(
                "max_depth 不能小于 0。"
            )

        root = self._resolve_path(path)

        if not root.exists():
            raise FileNotFoundError(
                f"路径不存在：{root}"
            )

        if not root.is_dir():
            raise NotADirectoryError(
                f"目标不是目录：{root}"
            )

        lines = [f"{root.name}/"]

        def walk_directory(
            directory: Path,
            prefix: str,
            depth: int,
        ) -> None:
            if depth >= max_depth:
                return

            entries = [
                entry
                for entry in directory.iterdir()
                if entry.name
                not in self.IGNORED_DIRECTORIES
            ]

            entries.sort(
                key=lambda entry: (
                    not entry.is_dir(),
                    entry.name.lower(),
                )
            )

            for index, entry in enumerate(entries):
                is_last = index == len(entries) - 1

                branch = (
                    "└── "
                    if is_last
                    else "├── "
                )

                suffix = "/" if entry.is_dir() else ""

                lines.append(
                    f"{prefix}{branch}"
                    f"{entry.name}{suffix}"
                )

                if entry.is_dir():
                    child_prefix = (
                        prefix
                        + (
                            "    "
                            if is_last
                            else "│   "
                        )
                    )

                    walk_directory(
                        directory=entry,
                        prefix=child_prefix,
                        depth=depth + 1,
                    )

        walk_directory(
            directory=root,
            prefix="",
            depth=0,
        )

        return self._truncate_output(
            "\n".join(lines)
        )
    



    def _read_file(
        self,
        path: str | Path,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> str:
        """
        按行读取文本文件。

        行号从 1 开始。
        """

        if not isinstance(start_line, int):
            raise TypeError(
                "start_line 必须是整数。"
            )

        if start_line <= 0:
            raise ValueError(
                "start_line 必须大于 0。"
            )

        if end_line is not None:
            if not isinstance(end_line, int):
                raise TypeError(
                    "end_line 必须是整数或 None。"
                )

            if end_line < start_line:
                raise ValueError(
                    "end_line 不能小于 start_line。"
                )

        file_path = self._resolve_path(path)

        self._validate_readable_file(file_path)

        try:
            text = file_path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError as error:
            raise ValueError(
                f"文件不是有效的 UTF-8 文本：{file_path}"
            ) from error

        lines = text.splitlines()

        if start_line > len(lines):
            return (
                f"文件共有 {len(lines)} 行，"
                f"start_line={start_line} 超出范围。"
            )

        start_index = start_line - 1

        if end_line is None:
            end_index = len(lines)
        else:
            end_index = min(
                end_line,
                len(lines),
            )

        selected_lines = lines[
            start_index:end_index
        ]

        numbered_lines = [
            f"{line_number:>4}: {line}"
            for line_number, line in enumerate(
                selected_lines,
                start=start_line,
            )
        ]

        header = (
            f"文件："
            f"{file_path.relative_to(self.workspace).as_posix()}\n"
            f"行范围：{start_line}-{end_index}\n\n"
        )

        return self._truncate_output(
            header + "\n".join(numbered_lines)
        )
    


    def _search_text(
        self,
        query: str,
        path: str | Path = ".",
        case_sensitive: bool = False,
        max_results: int = 50,
    ) -> str:
        """
        在目录中的文本文件里搜索关键词。
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

        if max_results <= 0:
            raise ValueError(
                "max_results 必须大于 0。"
            )

        target_path = self._resolve_path(path)

        if not target_path.exists():
            raise FileNotFoundError(
                f"路径不存在：{target_path}"
            )

        if target_path.is_file():
            candidate_files = [target_path]
        else:
            candidate_files = [
                file_path
                for file_path in target_path.rglob("*")
                if file_path.is_file()
                and not any(
                    part in self.IGNORED_DIRECTORIES
                    for part in file_path.parts
                )
            ]

        results: list[str] = []

        search_query = (
            query
            if case_sensitive
            else query.lower()
        )

        for file_path in candidate_files:
            if self._is_sensitive_file(file_path):
                continue

            if not self._is_allowed_text_file(file_path):
                continue

            try:
                if (
                    file_path.stat().st_size
                    > self.max_file_size
                ):
                    continue

                text = file_path.read_text(
                    encoding="utf-8"
                )
            except (
                OSError,
                UnicodeDecodeError,
            ):
                continue

            for line_number, line in enumerate(
                text.splitlines(),
                start=1,
            ):
                searchable_line = (
                    line
                    if case_sensitive
                    else line.lower()
                )

                if search_query not in searchable_line:
                    continue

                relative_path = file_path.relative_to(
                    self.workspace
                ).as_posix()

                results.append(
                    f"{relative_path}:"
                    f"{line_number}: "
                    f"{line.strip()}"
                )

                if len(results) >= max_results:
                    break

            if len(results) >= max_results:
                break

        if not results:
            return (
                f"没有找到包含“{query}”的内容。"
            )

        output = "\n".join(results)

        if len(results) >= max_results:
            output += (
                "\n\n"
                f"[结果最多显示 {max_results} 条]"
            )

        return self._truncate_output(output)
    



    def _file_info(
        self,
        path: str | Path,
    ) -> str:
        """
        查看文件或目录的基础信息。
        """

        target_path = self._resolve_path(path)

        if not target_path.exists():
            raise FileNotFoundError(
                f"路径不存在：{target_path}"
            )

        stat_result = target_path.stat()

        modified_time = datetime.fromtimestamp(
            stat_result.st_mtime
        ).isoformat(
            timespec="seconds"
        )

        relative_path = target_path.relative_to(
            self.workspace
        )

        path_type = (
            "目录"
            if target_path.is_dir()
            else "文件"
        )

        return (
            f"路径：{relative_path.as_posix()}\n"
            f"类型：{path_type}\n"
            f"大小：{stat_result.st_size} bytes\n"
            f"修改时间：{modified_time}"
        )

    def _change_dir(
        self,
        path: str | Path = ".",
    ) -> str:
        """
        切换当前工作目录。
        """

        target_dir = self._resolve_path(path)

        if not target_dir.exists():
            raise FileNotFoundError(
                f"目录不存在：{target_dir}"
            )

        if not target_dir.is_dir():
            raise NotADirectoryError(
                f"目标不是目录：{target_dir}"
            )

        self.current_dir = target_dir

        relative_path = self.current_dir.relative_to(
            self.workspace
        )

        display_path = (
            "."
            if str(relative_path) == "."
            else relative_path.as_posix()
        )

        return f"当前目录已切换为：{display_path}"
    


    def run(
        self,
        parameters: dict[str, Any],
    ) -> str:
        """
        根据 action 执行文件系统操作。
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

        if action not in self.SUPPORTED_ACTIONS:
            supported = "、".join(
                sorted(self.SUPPORTED_ACTIONS)
            )

            raise ValueError(
                f"不支持的 action：{action}。"
                f"当前支持：{supported}。"
            )

        if action == "pwd":
            return self._pwd()

        if action == "list_files":
            return self._list_files(
                path=parameters.get(
                    "path",
                    ".",
                ),
                show_hidden=parameters.get(
                    "show_hidden",
                    False,
                ),
            )

        if action == "tree":
            return self._tree(
                path=parameters.get(
                    "path",
                    ".",
                ),
                max_depth=parameters.get(
                    "max_depth",
                    3,
                ),
            )

        if action == "read_file":
            return self._read_file(
                path=parameters.get(
                    "path",
                    "",
                ),
                start_line=parameters.get(
                    "start_line",
                    1,
                ),
                end_line=parameters.get(
                    "end_line",
                ),
            )

        if action == "search_text":
            return self._search_text(
                query=parameters.get(
                    "query",
                    "",
                ),
                path=parameters.get(
                    "path",
                    ".",
                ),
                case_sensitive=parameters.get(
                    "case_sensitive",
                    False,
                ),
                max_results=parameters.get(
                    "max_results",
                    50,
                ),
            )

        if action == "file_info":
            return self._file_info(
                path=parameters.get(
                    "path",
                    "",
                ),
            )

        if action == "change_dir":
            return self._change_dir(
                path=parameters.get(
                    "path",
                    ".",
                ),
            )

        raise RuntimeError(
            "未处理的 TerminalTool action。"
        )
    



