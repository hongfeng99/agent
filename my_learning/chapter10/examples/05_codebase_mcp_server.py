import json
import os
import ast

from pathlib import Path
from typing import Any

from hello_agents.protocols import MCPServer


# 当前文件路径：
#
# hello-agents/
# └── my_learning/
#     └── chapter10/
#         └── examples/
#             └── 05_codebase_mcp_server.py
#
# parents[3] 对应 hello-agents 项目根目录。
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 允许通过环境变量覆盖项目根目录，方便以后复用服务器。
PROJECT_ROOT = Path(
    os.getenv("CODEBASE_PROJECT_ROOT", str(DEFAULT_PROJECT_ROOT))
).resolve()

# 搜索代码时忽略这些目录。
IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "site-packages",
}

# 当前服务器只允许读取这些文本文件。
ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
}

def read_python_symbol(
    path: str,
    symbol: str,
) -> str:
    """
    精确读取 Python 文件中的类或方法。

    symbol 示例：
        ContextBuilder
        ContextBuilder.build
        ContextBuilder._gather
        ContextBuilder._select
    """

    source_path = resolve_safe_path(path)

    if not source_path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")

    if not source_path.is_file():
        raise IsADirectoryError(f"指定路径不是文件：{path}")

    if source_path.suffix.lower() != ".py":
        raise ValueError("read_python_symbol 只支持 Python 文件。")

    source = source_path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)

    symbol_parts = symbol.split(".")

    target_node: ast.AST | None = None

    if len(symbol_parts) == 1:
        target_name = symbol_parts[0]

        for node in tree.body:
            if isinstance(
                node,
                (
                    ast.ClassDef,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ) and node.name == target_name:
                target_node = node
                break

    elif len(symbol_parts) == 2:
        class_name, member_name = symbol_parts

        for node in tree.body:
            if not (
                isinstance(node, ast.ClassDef)
                and node.name == class_name
            ):
                continue

            for member in node.body:
                if isinstance(
                    member,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ) and member.name == member_name:
                    target_node = member
                    break

            break

    else:
        raise ValueError(
            "symbol 只支持 ClassName 或 ClassName.method_name 格式。"
        )

    if target_node is None:
        raise LookupError(
            f"在 {path} 中没有找到符号：{symbol}"
        )

    start_line = target_node.lineno
    end_line = getattr(
        target_node,
        "end_lineno",
        start_line,
    )

    selected_lines = lines[start_line - 1:end_line]

    content = "\n".join(
        f"{line_number:>4}: {line}"
        for line_number, line in enumerate(
            selected_lines,
            start=start_line,
        )
    )

    return to_json(
        {
            "path": source_path.relative_to(
                PROJECT_ROOT
            ).as_posix(),
            "symbol": symbol,
            "start_line": start_line,
            "end_line": end_line,
            "content": content,
        }
    )



def to_json(data: Any) -> str:
    """
    将 Python 数据转换成格式化 JSON 字符串。
    """

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )


def resolve_safe_path(relative_path: str) -> Path:
    """
    将相对路径转换成项目内的安全绝对路径。

    禁止：
    1. 绝对路径；
    2. 通过 ../ 离开项目根目录；
    3. 空路径。
    """

    if not relative_path or not relative_path.strip():
        raise ValueError("路径不能为空。")

    path = Path(relative_path)

    if path.is_absolute():
        raise ValueError("只允许使用相对于项目根目录的路径。")

    resolved_path = (PROJECT_ROOT / path).resolve()

    try:
        resolved_path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise PermissionError(
            f"禁止访问项目根目录之外的路径：{relative_path}"
        ) from exc

    return resolved_path


def should_ignore(path: Path) -> bool:
    """
    判断路径中是否包含应忽略的目录。
    """

    try:
        relative_parts = path.relative_to(PROJECT_ROOT).parts
    except ValueError:
        return True

    return any(
        part in IGNORED_DIRECTORIES
        for part in relative_parts
    )


def get_project_summary() -> str:
    """
    获取当前代码项目的基础摘要。

    返回项目根目录、Python 文件数量、Python 代码总行数，
    以及项目根目录中的主要文件和目录。
    """

    python_file_count = 0
    python_line_count = 0

    for path in PROJECT_ROOT.rglob("*.py"):
        if should_ignore(path):
            continue

        python_file_count += 1

        try:
            content = path.read_text(encoding="utf-8")
            python_line_count += len(content.splitlines())
        except (OSError, UnicodeDecodeError):
            continue

    top_level_items = sorted(
        item.name
        for item in PROJECT_ROOT.iterdir()
        if item.name not in IGNORED_DIRECTORIES
    )

    result = {
        "project_root": str(PROJECT_ROOT),
        "python_file_count": python_file_count,
        "python_line_count": python_line_count,
        "top_level_items": top_level_items,
    }

    return to_json(result)


def list_python_files(
    relative_directory: str = ".",
    max_results: int = 200,
) -> str:
    """
    列出指定项目目录中的 Python 文件。

    参数：
        relative_directory:
            相对于项目根目录的目录，例如：
            "."、"my_learning/chapter9"。

        max_results:
            最多返回多少个文件，范围为 1～500。
    """

    if max_results < 1 or max_results > 500:
        raise ValueError("max_results 必须在 1～500 之间。")

    directory = resolve_safe_path(relative_directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"目录不存在：{relative_directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"指定路径不是目录：{relative_directory}"
        )

    files: list[str] = []

    for path in directory.rglob("*.py"):
        if should_ignore(path):
            continue

        files.append(
            path.relative_to(PROJECT_ROOT).as_posix()
        )

        if len(files) >= max_results:
            break

    result = {
        "relative_directory": relative_directory,
        "count": len(files),
        "files": sorted(files),
        "truncated": len(files) >= max_results,
    }

    return to_json(result)


def search_symbol(
    keyword: str,
    relative_directory: str = ".",
    max_results: int = 30,
) -> str:
    """
    在 Python 文件中搜索类名、函数名或其他关键字。

    参数：
        keyword:
            要查找的内容，例如 ContextBuilder。

        relative_directory:
            搜索范围，例如 "." 或 "my_learning/chapter9"。

        max_results:
            最多返回多少条匹配结果，范围为 1～100。
    """

    keyword = keyword.strip()

    if not keyword:
        raise ValueError("keyword 不能为空。")

    if max_results < 1 or max_results > 100:
        raise ValueError("max_results 必须在 1～100 之间。")

    directory = resolve_safe_path(relative_directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"目录不存在：{relative_directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"指定路径不是目录：{relative_directory}"
        )

    matches: list[dict[str, Any]] = []
    normalized_keyword = keyword.casefold()

    for path in directory.rglob("*.py"):
        if should_ignore(path):
            continue

        try:
            lines = path.read_text(
                encoding="utf-8"
            ).splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for line_number, line in enumerate(lines, start=1):
            if normalized_keyword not in line.casefold():
                continue

            matches.append(
                {
                    "path": path.relative_to(
                        PROJECT_ROOT
                    ).as_posix(),
                    "line_number": line_number,
                    "content": line.strip(),
                }
            )

            if len(matches) >= max_results:
                return to_json(
                    {
                        "keyword": keyword,
                        "count": len(matches),
                        "matches": matches,
                        "truncated": True,
                    }
                )

    return to_json(
        {
            "keyword": keyword,
            "count": len(matches),
            "matches": matches,
            "truncated": False,
        }
    )


def read_source_file(
    path: str,
    start_line: int = 1,
    end_line: int = 200,
) -> str:
    """
    按行读取项目中的文本源码文件。

    返回内容包含行号，方便模型引用和分析。

    参数：
        path:
            相对于项目根目录的文件路径。

        start_line:
            开始行号，从 1 开始。

        end_line:
            结束行号，单次最多读取 300 行。
    """

    source_path = resolve_safe_path(path)

    if not source_path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")

    if not source_path.is_file():
        raise IsADirectoryError(f"指定路径不是文件：{path}")

    if source_path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(
            f"不支持读取 {source_path.suffix} 文件。"
            f"允许的类型：{sorted(ALLOWED_SUFFIXES)}"
        )

    if start_line < 1:
        raise ValueError("start_line 必须大于或等于 1。")

    if end_line < start_line:
        raise ValueError(
            "end_line 必须大于或等于 start_line。"
        )

    if end_line - start_line + 1 > 300:
        raise ValueError("单次最多读取 300 行。")

    try:
        lines = source_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"文件不是有效的 UTF-8 文本：{path}"
        ) from exc

    total_lines = len(lines)

    selected_lines = lines[start_line - 1:end_line]

    numbered_content = "\n".join(
        f"{line_number:>4}: {line}"
        for line_number, line in enumerate(
            selected_lines,
            start=start_line,
        )
    )

    result = {
        "path": source_path.relative_to(
            PROJECT_ROOT
        ).as_posix(),
        "start_line": start_line,
        "end_line": min(end_line, total_lines),
        "total_lines": total_lines,
        "content": numbered_content,
    }

    return to_json(result)


# 创建 MCP Server。
codebase_server = MCPServer(
    name="codebase-server",
    description="用于安全查看和分析当前 Python 项目的只读 MCP 服务",
)

# 将普通 Python 函数注册为 MCP 工具。
codebase_server.add_tool(get_project_summary)
codebase_server.add_tool(list_python_files)
codebase_server.add_tool(search_symbol)
codebase_server.add_tool(read_source_file)
codebase_server.add_tool(read_python_symbol)

if __name__ == "__main__":
    # MCP 的 Stdio Transport 使用标准输入和标准输出通信。
    #
    # 服务器运行期间不要随意 print()，
    # 否则普通输出可能干扰 MCP 协议消息。
    codebase_server.run()