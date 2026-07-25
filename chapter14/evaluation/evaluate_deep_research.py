import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from chapter14.backend.dependencies import (
    create_deep_research_agent,
)
from chapter14.backend.models import (
    ResearchState,
    ResearchStatus,
    TaskStatus,
)
from chapter14.backend.utils.source_utils import (
    normalize_url,
)


PROJECT_ROOT = Path(__file__).resolve().parent

TEST_CASES_PATH = (
    PROJECT_ROOT / "test_cases.json"
)

RESULTS_DIR = PROJECT_ROOT / "results"


REQUIRED_REPORT_SECTIONS = [
    "## 摘要",
    "## 研究背景",
    "## 主要发现",
    "## 综合分析",
    "## 局限性",
    "## 结论",
    "## 参考资料",
]


def load_test_cases() -> list[dict[str, Any]]:
    """
    读取评估用例。
    """

    if not TEST_CASES_PATH.exists():
        raise FileNotFoundError(
            f"找不到测试用例文件："
            f"{TEST_CASES_PATH}"
        )

    raw_text = TEST_CASES_PATH.read_text(
        encoding="utf-8",
    )

    test_cases = json.loads(raw_text)

    if not isinstance(test_cases, list):
        raise ValueError(
            "test_cases.json 的顶层结构必须是数组。"
        )

    return test_cases


def select_test_cases(
    test_cases: list[dict[str, Any]],
    case_id: str | None,
    run_all: bool,
) -> list[dict[str, Any]]:
    """
    根据命令行参数选择需要执行的用例。
    """

    if run_all:
        return test_cases

    if case_id is None:
        return test_cases[:1]

    selected_cases = [
        case
        for case in test_cases
        if case.get("id") == case_id
    ]

    if not selected_cases:
        raise ValueError(
            f"没有找到测试用例：{case_id}"
        )

    return selected_cases


def collect_source_urls(
    state: ResearchState,
) -> list[str]:
    """
    收集所有子任务中的来源 URL。
    """

    urls: list[str] = []

    for summary in state.summaries:
        for source in summary.sources:
            normalized_url = normalize_url(
                source.url
            )

            if normalized_url:
                urls.append(normalized_url)

    return urls


def count_report_citations(
    report: str,
) -> int:
    """
    统计报告中形如 [1]、[2] 的引用标记数量。
    """

    citations = re.findall(
        r"\[\d+\]",
        report,
    )

    return len(citations)


def evaluate_state(
    state: ResearchState,
    expected_keywords: list[str],
    report_path: Path | None,
) -> dict[str, Any]:
    """
    根据固定规则评估一次研究结果。

    总分为 100 分。
    """

    details: dict[str, Any] = {}

    score = 0

    # 1. 研究是否正常完成：10 分
    workflow_completed = (
        state.status
        == ResearchStatus.COMPLETED
    )

    details["workflow_completed"] = (
        workflow_completed
    )

    if workflow_completed:
        score += 10

    # 2. 任务数量是否为 3～5 个：10 分
    task_count = len(state.tasks)

    valid_task_count = (
        3 <= task_count <= 5
    )

    details["task_count"] = task_count
    details["valid_task_count"] = (
        valid_task_count
    )

    if valid_task_count:
        score += 10

    # 3. 所有子任务是否完成：15 分
    completed_task_count = sum(
        task.status
        == TaskStatus.COMPLETED
        for task in state.tasks
    )

    all_tasks_completed = (
        task_count > 0
        and completed_task_count
        == task_count
    )

    details["completed_task_count"] = (
        completed_task_count
    )

    details["all_tasks_completed"] = (
        all_tasks_completed
    )

    if all_tasks_completed:
        score += 15

    # 4. 每个任务是否都有总结：15 分
    summary_count = len(
        state.summaries
    )

    summaries_complete = (
        task_count > 0
        and summary_count == task_count
    )

    details["summary_count"] = (
        summary_count
    )

    details["summaries_complete"] = (
        summaries_complete
    )

    if summaries_complete:
        score += 15

    # 5. 是否获得足够的资料来源：15 分
    source_urls = collect_source_urls(
        state
    )

    unique_source_urls = set(
        source_urls
    )

    source_count = len(source_urls)
    unique_source_count = len(
        unique_source_urls
    )

    has_sufficient_sources = (
        task_count > 0
        and unique_source_count
        >= task_count
    )

    details["source_count"] = (
        source_count
    )

    details["unique_source_count"] = (
        unique_source_count
    )

    details["duplicate_source_count"] = (
        source_count
        - unique_source_count
    )

    details["has_sufficient_sources"] = (
        has_sufficient_sources
    )

    if has_sufficient_sources:
        score += 15

    # 6. 报告结构是否完整：20 分
    report = state.final_report

    present_sections = [
        section
        for section in REQUIRED_REPORT_SECTIONS
        if section in report
    ]

    section_ratio = (
        len(present_sections)
        / len(REQUIRED_REPORT_SECTIONS)
    )

    section_score = round(
        section_ratio * 20
    )

    score += section_score

    details["present_sections"] = (
        present_sections
    )

    details["missing_sections"] = [
        section
        for section in REQUIRED_REPORT_SECTIONS
        if section not in report
    ]

    details["section_score"] = (
        section_score
    )

    # 7. 报告是否包含引用：10 分
    citation_count = (
        count_report_citations(report)
    )

    has_citations = citation_count > 0

    details["citation_count"] = (
        citation_count
    )

    details["has_citations"] = (
        has_citations
    )

    if has_citations:
        score += 10

    # 8. 报告是否包含预期关键词：3 分
    matched_keywords = [
        keyword
        for keyword in expected_keywords
        if keyword.casefold()
        in report.casefold()
    ]

    keyword_coverage = (
        len(matched_keywords)
        / len(expected_keywords)
        if expected_keywords
        else 1.0
    )

    keyword_score = round(
        keyword_coverage * 3
    )

    score += keyword_score

    details["matched_keywords"] = (
        matched_keywords
    )

    details["missing_keywords"] = [
        keyword
        for keyword in expected_keywords
        if keyword not in matched_keywords
    ]

    # 9. 报告文件是否成功保存：2 分
    report_saved = (
        report_path is not None
        and report_path.exists()
    )

    details["report_saved"] = (
        report_saved
    )

    details["report_path"] = (
        str(report_path)
        if report_path is not None
        else None
    )

    if report_saved:
        score += 2

    details["score"] = score
    details["passed"] = score >= 80

    return details


def print_event(
    event_type: str,
    message: str,
    data: dict[str, Any],
) -> None:
    """
    打印研究过程中的关键事件。
    """

    print(
        f"[{event_type}] {message}"
    )


def evaluate_case(
    test_case: dict[str, Any],
) -> dict[str, Any]:
    """
    执行并评估一个真实研究用例。
    """

    case_id = str(
        test_case["id"]
    )

    topic = str(
        test_case["topic"]
    )

    expected_keywords = [
        str(keyword)
        for keyword
        in test_case.get(
            "expected_keywords",
            [],
        )
    ]

    print()
    print("=" * 72)
    print(f"评估用例：{case_id}")
    print("=" * 72)
    print(f"研究主题：{topic}")
    print()

    started_at = datetime.now()

    agent = create_deep_research_agent(
        event_handler=print_event,
    )

    try:
        state = agent.research(
            topic
        )

        report_path = (
            agent.last_report_path
        )

        evaluation = evaluate_state(
            state=state,
            expected_keywords=(
                expected_keywords
            ),
            report_path=report_path,
        )

        error_message = None

    except Exception as exc:
        state = None

        evaluation = {
            "score": 0,
            "passed": False,
            "workflow_completed": False,
        }

        error_message = str(exc)

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at - started_at
    ).total_seconds()

    result = {
        "case_id": case_id,
        "topic": topic,
        "started_at": (
            started_at.isoformat(
                timespec="seconds"
            )
        ),
        "finished_at": (
            finished_at.isoformat(
                timespec="seconds"
            )
        ),
        "elapsed_seconds": round(
            elapsed_seconds,
            2,
        ),
        "run_id": agent.last_run_id,
        "evaluation": evaluation,
        "error_message": error_message,
    }

    print()
    print("-" * 72)
    print(
        f"评估得分："
        f"{evaluation['score']}/100"
    )
    print(
        f"评估结果："
        f"{'通过' if evaluation['passed'] else '未通过'}"
    )
    print(
        f"执行时间："
        f"{elapsed_seconds:.2f} 秒"
    )

    if error_message:
        print(
            f"错误信息：{error_message}"
        )

    return result


def save_evaluation_results(
    results: list[dict[str, Any]],
) -> Path:
    """
    将评估结果保存为 JSON。
    """

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    result_path = RESULTS_DIR / (
        f"evaluation_{timestamp}.json"
    )

    result_data = {
        "case_count": len(results),
        "passed_count": sum(
            result["evaluation"]["passed"]
            for result in results
        ),
        "average_score": round(
            sum(
                result["evaluation"]["score"]
                for result in results
            )
            / len(results),
            2,
        ),
        "results": results,
    }

    result_path.write_text(
        json.dumps(
            result_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return result_path


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数。
    """

    parser = argparse.ArgumentParser(
        description=(
            "评估 Chapter 14 "
            "Deep Research Agent"
        )
    )

    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help="只执行指定 ID 的测试用例",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="执行全部测试用例",
    )

    return parser.parse_args()


def main() -> None:
    """
    运行端到端评估。
    """

    arguments = parse_arguments()

    test_cases = load_test_cases()

    selected_cases = select_test_cases(
        test_cases=test_cases,
        case_id=arguments.case_id,
        run_all=arguments.all,
    )

    print("=" * 72)
    print("Chapter 14 Deep Research Agent 端到端评估")
    print("=" * 72)
    print(
        f"本次执行用例数量："
        f"{len(selected_cases)}"
    )

    results = [
        evaluate_case(test_case)
        for test_case in selected_cases
    ]

    result_path = save_evaluation_results(
        results
    )

    print()
    print("=" * 72)
    print("评估完成")
    print("=" * 72)

    passed_count = sum(
        result["evaluation"]["passed"]
        for result in results
    )

    average_score = (
        sum(
            result["evaluation"]["score"]
            for result in results
        )
        / len(results)
    )

    print(
        f"通过用例："
        f"{passed_count}/{len(results)}"
    )

    print(
        f"平均得分："
        f"{average_score:.2f}/100"
    )

    print(
        f"结果文件："
        f"{result_path.resolve()}"
    )


if __name__ == "__main__":
    main()