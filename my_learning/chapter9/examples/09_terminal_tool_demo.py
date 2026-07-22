import sys
from pathlib import Path


CHAPTER9_DIR = (
    Path(__file__).resolve().parent.parent
)

PROJECT_DIR = CHAPTER9_DIR.parent.parent

sys.path.insert(
    0,
    str(CHAPTER9_DIR),
)


from tools import TerminalTool


def main() -> None:
    """
    测试 TerminalTool 的基本功能。
    """

    terminal = TerminalTool(
        workspace=PROJECT_DIR,
        max_output_chars=10_000,
        max_file_size=1_000_000,
    )

    print("=" * 70)
    print("1. 查看当前目录")
    print("=" * 70)

    print(
        terminal.run({
            "action": "pwd",
        })
    )

    print("\n" + "=" * 70)
    print("2. 查看 Chapter 9 目录")
    print("=" * 70)

    print(
        terminal.run({
            "action": "list_files",
            "path": "my_learning/chapter9",
        })
    )

    print("\n" + "=" * 70)
    print("3. 查看 Chapter 9 目录树")
    print("=" * 70)

    print(
        terminal.run({
            "action": "tree",
            "path": "my_learning/chapter9",
            "max_depth": 2,
        })
    )

    print("\n" + "=" * 70)
    print("4. 读取 ContextBuilder 部分代码")
    print("=" * 70)

    print(
        terminal.run({
            "action": "read_file",
            "path": (
                "my_learning/chapter9/"
                "context/builder.py"
            ),
            "start_line": 1,
            "end_line": 40,
        })
    )

    print("\n" + "=" * 70)
    print("5. 搜索 ContextBuilder")
    print("=" * 70)

    print(
        terminal.run({
            "action": "search_text",
            "query": "class ContextBuilder",
            "path": "my_learning/chapter9",
            "max_results": 10,
        })
    )

    print("\n" + "=" * 70)
    print("6. 查看文件信息")
    print("=" * 70)

    print(
        terminal.run({
            "action": "file_info",
            "path": (
                "my_learning/chapter9/"
                "context/builder.py"
            ),
        })
    )

    print("\n" + "=" * 70)
    print("7. 测试路径逃逸")
    print("=" * 70)

    try:
        print(
            terminal.run({
                "action": "list_files",
                "path": "../../../",
            })
        )
    except PermissionError as error:
        print(f"成功拦截：{error}")

    print("\n" + "=" * 70)
    print("8. 测试敏感文件读取")
    print("=" * 70)

    try:
        print(
            terminal.run({
                "action": "read_file",
                "path": ".env",
            })
        )
    except (
        PermissionError,
        FileNotFoundError,
    ) as error:
        print(f"成功拦截：{error}")


if __name__ == "__main__":
    main()