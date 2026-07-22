import json
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


from agents import CodebaseMaintainer


class FakeLLM:
    """
    用于测试整体流程的模拟大模型。
    """

    def __init__(self) -> None:
        self.last_prompt = ""

    def invoke(
        self,
        prompt: str,
    ) -> str:
        """
        保存收到的上下文，并返回模拟回答。
        """

        self.last_prompt = prompt

        return (
            "模拟回答：已经收到代码结构、"
            "代码搜索结果和相关项目笔记。"
        )


def main() -> None:
    fake_llm = FakeLLM()

    maintainer = CodebaseMaintainer(
        project_name="hello_agents_chapter9",
        codebase_path=PROJECT_DIR,
        llm=fake_llm,
        notes_workspace=(
            CHAPTER9_DIR
            / "data"
            / "maintainer_demo_notes"
        ),
        focus_path="my_learning/chapter9",
    )

    # 创建一条长期项目笔记。
    maintainer.record_note(
        title="Chapter 9 当前进度",
        content=(
            "ContextBuilder、NoteTool、TerminalTool "
            "以及两个适配器均已完成。"
        ),
        note_type="task_state",
        tags=[
            "chapter9",
            "progress",
        ],
    )

    response = maintainer.run(
        user_input=(
            "请分析 ContextBuilder 的主要职责。"
        ),
        mode="auto",
    )

    print("\nLLM 返回：")
    print(response)

    print("\nLLM 实际收到的上下文：")
    print("-" * 70)
    print(fake_llm.last_prompt)
    print("-" * 70)

    print("\n运行统计：")
    print(
        json.dumps(
            maintainer.get_stats(),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()