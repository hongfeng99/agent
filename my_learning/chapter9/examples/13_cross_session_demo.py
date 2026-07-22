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


class IssueLLM:
    """
    第一次会话使用的模拟模型。

    模拟模型在代码分析中发现问题，
    从而触发 blocker 笔记创建。
    """

    def invoke(
        self,
        prompt: str,
    ) -> str:
        return (
            "发现问题：DemoService 当前缺少单元测试，"
            "并且异常处理不完整，运行失败时难以定位原因。"
        )


class PlanLLM:
    """
    第二次会话使用的模拟模型。

    保存收到的上下文，用于确认之前的 blocker
    是否重新进入新会话。
    """

    def __init__(self) -> None:
        self.last_prompt = ""

    def invoke(
        self,
        prompt: str,
    ) -> str:
        self.last_prompt = prompt

        return (
            "下一步计划：先为 DemoService 补充单元测试，"
            "然后完善异常处理，最后重新运行全部测试。"
        )


def prepare_demo_project(
    project_dir: Path,
) -> None:
    """
    创建一个简单的演示项目。
    """

    src_dir = project_dir / "src"

    src_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    service_file = src_dir / "service.py"

    service_file.write_text(
        "class DemoService:\n"
        "    def run(self) -> str:\n"
        "        return 'done'\n",
        encoding="utf-8",
    )


def main() -> None:
    demo_project = (
        CHAPTER9_DIR
        / "data"
        / "cross_session_project"
    )

    notes_workspace = (
        CHAPTER9_DIR
        / "data"
        / "cross_session_notes"
    )

    prepare_demo_project(
        demo_project
    )

    # =====================================================
    # 第一次会话：分析代码并创建 blocker
    # =====================================================

    first_maintainer = CodebaseMaintainer(
        project_name="cross_session_demo",
        codebase_path=demo_project,
        llm=IssueLLM(),
        notes_workspace=notes_workspace,
        focus_path=".",
    )

    print("=" * 70)
    print("第一次会话：分析代码")
    print("=" * 70)

    first_response = first_maintainer.run(
        user_input="请分析 DemoService 的实现。",
        mode="analyze",
    )

    print("\n第一次回答：")
    print(first_response)

    first_report = (
        first_maintainer.generate_report()
    )

    print("\n第一次会话报告：")
    print(
        json.dumps(
            first_report,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    blockers = first_maintainer.note_tool.run({
        "action": "list",
        "note_type": "blocker",
    })

    print(
        "\n第一次会话创建的 blocker 数量："
        f"{len(blockers)}"
    )

    # =====================================================
    # 第二次会话：重新创建 CodebaseMaintainer
    # =====================================================

    plan_llm = PlanLLM()

    second_maintainer = CodebaseMaintainer(
        project_name="cross_session_demo",
        codebase_path=demo_project,
        llm=plan_llm,
        notes_workspace=notes_workspace,
        focus_path=".",
    )

    print("\n" + "=" * 70)
    print("第二次会话：根据历史问题制定计划")
    print("=" * 70)

    second_response = second_maintainer.run(
        user_input=(
            "请根据之前发现的问题，"
            "制定 DemoService 的下一步计划。"
        ),
        mode="plan",
    )

    print("\n第二次回答：")
    print(second_response)

    print("\n第二次模型是否看到旧 blocker：")

    if (
        "DemoService 当前缺少单元测试"
        in plan_llm.last_prompt
    ):
        print("成功：旧 blocker 已进入新会话上下文。")
    else:
        print("失败：新会话没有检索到旧 blocker。")

    print("\n第二次模型收到的上下文：")
    print("-" * 70)
    print(plan_llm.last_prompt)
    print("-" * 70)


if __name__ == "__main__":
    main()