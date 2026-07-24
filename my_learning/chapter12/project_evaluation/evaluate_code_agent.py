import argparse
import csv
import json
import math
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

import requests


# 当前评估目录。
BASE_DIR = Path(__file__).resolve().parent

# 默认测试数据和报告目录。
DEFAULT_CASE_FILE = BASE_DIR / "test_cases.json"
RESULTS_DIR = BASE_DIR / "results"


def load_test_cases(
    case_file: Path,
) -> list[dict[str, Any]]:
    """
    加载测试用例，并将 defaults 合并到每个测试用例中。
    """

    if not case_file.exists():
        raise FileNotFoundError(
            f"找不到测试用例文件：{case_file}"
        )

    with case_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise TypeError(
            "测试用例文件顶层必须是 JSON 对象。"
        )

    defaults = payload.get("defaults", {})
    cases = payload.get("cases", [])

    if not isinstance(defaults, dict):
        raise TypeError(
            "defaults 必须是 JSON 对象。"
        )

    if not isinstance(cases, list):
        raise TypeError(
            "cases 必须是 JSON 数组。"
        )

    merged_cases: list[dict[str, Any]] = []

    for index, case in enumerate(
        cases,
        start=1,
    ):
        if not isinstance(case, dict):
            raise TypeError(
                f"第 {index} 个测试用例不是 JSON 对象。"
            )

        merged_case = {
            **defaults,
            **case,
        }

        if not merged_case.get("id"):
            raise ValueError(
                f"第 {index} 个测试用例缺少 id。"
            )

        if not merged_case.get("question"):
            raise ValueError(
                f"测试用例 {merged_case['id']} "
                "缺少 question。"
            )

        merged_cases.append(merged_case)

    if not merged_cases:
        raise ValueError(
            "测试用例列表为空。"
        )

    return merged_cases


def parse_agent_result(
    response_data: Any,
) -> dict[str, Any]:
    """
    解析 A2A /ask 接口返回的数据。

    常见格式为：

    {
        "answer": "{...远程 Agent 返回的 JSON 字符串...}"
    }
    """

    if not isinstance(response_data, dict):
        raise TypeError(
            "A2A 响应顶层不是 JSON 对象。"
        )

    # 兼容直接返回业务结果的情况。
    if (
        "status" in response_data
        and "answer" not in response_data
    ):
        return response_data

    answer = response_data.get("answer")

    if isinstance(answer, dict):
        return answer

    if isinstance(answer, str):
        try:
            parsed_answer = json.loads(answer)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "A2A answer 字段不是有效 JSON。"
            ) from exc

        if not isinstance(parsed_answer, dict):
            raise TypeError(
                "A2A answer 解析后不是 JSON 对象。"
            )

        return parsed_answer

    raise TypeError(
        "A2A 响应中没有有效的 answer 字段。"
    )


def call_remote_agent(
    endpoint: str,
    question: str,
    timeout: int,
) -> tuple[dict[str, Any], float]:
    """
    通过 A2A /ask 接口调用远程 Agent。

    返回：
        result:
            远程 Agent 的结构化结果。

        duration:
            从客户端测得的完整请求耗时。
    """

    ask_url = (
        f"{endpoint.rstrip('/')}/ask"
    )

    started_at = time.perf_counter()

    try:
        response = requests.post(
            ask_url,
            json={
                "question": question,
            },
            timeout=(5, timeout),
        )

        response.raise_for_status()

    except requests.Timeout as exc:
        raise TimeoutError(
            f"远程 Agent 在 {timeout} 秒内"
            "没有完成任务。"
        ) from exc

    except requests.RequestException as exc:
        raise ConnectionError(
            "A2A 请求失败："
            f"{type(exc).__name__}: {exc}"
        ) from exc

    duration = (
        time.perf_counter()
        - started_at
    )

    try:
        response_data = response.json()
    except requests.JSONDecodeError as exc:
        raise ValueError(
            "A2A Server 返回的不是有效 JSON。"
        ) from exc

    result = parse_agent_result(
        response_data
    )

    return result, duration


def find_missing_keywords(
    text: str,
    required_keywords: list[str],
) -> list[str]:
    """
    找出没有出现在文本中的必需关键词。

    比较时忽略英文大小写。
    """

    normalized_text = text.casefold()

    return [
        keyword
        for keyword in required_keywords
        if keyword.casefold()
        not in normalized_text
    ]


def find_forbidden_phrases(
    text: str,
    forbidden_phrases: list[str],
) -> list[str]:
    """
    找出回答中出现的禁止短语。
    """

    return [
        phrase
        for phrase in forbidden_phrases
        if phrase in text
    ]


def evaluate_result(
    case: dict[str, Any],
    result: dict[str, Any],
    duration: float,
) -> dict[str, Any]:
    """
    使用确定性规则检查一次 Agent 返回结果。
    """

    analysis = str(
        result.get("analysis", "")
    )

    actual_status = str(
        result.get("status", "")
    )

    expected_status = str(
        case.get(
            "expected_status",
            "completed",
        )
    )

    required_keywords = list(
        case.get(
            "required_keywords",
            [],
        )
    )

    required_symbols = set(
        case.get(
            "required_symbols",
            [],
        )
    )

    actual_symbols = set(
        result.get(
            "symbols_read",
            [],
        )
    )

    required_source_keywords = list(
        case.get(
            "required_data_source_keywords",
            [],
        )
    )

    data_source = str(
        result.get(
            "data_source",
            "",
        )
    )

    forbidden_phrases = list(
        case.get(
            "forbidden_phrases",
            [],
        )
    )

    max_seconds = float(
        case.get(
            "max_seconds",
            120,
        )
    )

    missing_keywords = (
        find_missing_keywords(
            analysis,
            required_keywords,
        )
    )

    missing_symbols = sorted(
        required_symbols - actual_symbols
    )

    missing_source_keywords = (
        find_missing_keywords(
            data_source,
            required_source_keywords,
        )
    )

    found_forbidden_phrases = (
        find_forbidden_phrases(
            analysis,
            forbidden_phrases,
        )
    )

    checks = {
        "status_correct": (
            actual_status
            == expected_status
        ),
        "keywords_complete": (
            not missing_keywords
        ),
        "symbols_complete": (
            not missing_symbols
        ),
        "data_source_valid": (
            not missing_source_keywords
        ),
        "no_incomplete_phrases": (
            not found_forbidden_phrases
        ),
        "latency_within_limit": (
            duration <= max_seconds
        ),
    }

    passed = all(
        checks.values()
    )

    return {
        "id": case["id"],
        "name": case.get(
            "name",
            case["id"],
        ),
        "question": case["question"],
        "passed": passed,
        "checks": checks,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "missing_keywords": missing_keywords,
        "missing_symbols": missing_symbols,
        "missing_source_keywords": (
            missing_source_keywords
        ),
        "found_forbidden_phrases": (
            found_forbidden_phrases
        ),
        "duration_seconds": round(
            duration,
            2,
        ),
        "server_elapsed_seconds": (
            result.get(
                "elapsed_seconds"
            )
        ),
        "data_source": data_source,
        "symbols_read": sorted(
            actual_symbols
        ),
        "analysis": analysis,
        "raw_result": result,
        "error": None,
    }


def create_error_result(
    case: dict[str, Any],
    exc: Exception,
    duration: float,
) -> dict[str, Any]:
    """
    当调用或解析失败时，生成失败记录。
    """

    return {
        "id": case["id"],
        "name": case.get(
            "name",
            case["id"],
        ),
        "question": case["question"],
        "passed": False,
        "checks": {
            "request_completed": False,
        },
        "expected_status": case.get(
            "expected_status",
            "completed",
        ),
        "actual_status": "error",
        "missing_keywords": [],
        "missing_symbols": [],
        "missing_source_keywords": [],
        "found_forbidden_phrases": [],
        "duration_seconds": round(
            duration,
            2,
        ),
        "server_elapsed_seconds": None,
        "data_source": "",
        "symbols_read": [],
        "analysis": "",
        "raw_result": None,
        "error": (
            f"{type(exc).__name__}: {exc}"
        ),
    }


def calculate_percentile(
    values: list[float],
    percentile: float,
) -> float:
    """
    计算一个简单的离散百分位数。

    例如：
        percentile=0.95 表示 P95。
    """

    if not values:
        return 0.0

    sorted_values = sorted(values)

    index = (
        math.ceil(
            percentile
            * len(sorted_values)
        )
        - 1
    )

    index = max(
        0,
        min(
            index,
            len(sorted_values) - 1,
        ),
    )

    return sorted_values[index]


def build_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    汇总整体评估结果。
    """

    total = len(results)

    passed_count = sum(
        1
        for result in results
        if result["passed"]
    )

    failed_count = (
        total - passed_count
    )

    durations = [
        float(result["duration_seconds"])
        for result in results
    ]

    pass_rate = (
        passed_count / total
        if total
        else 0.0
    )

    return {
        "total_cases": total,
        "passed_cases": passed_count,
        "failed_cases": failed_count,
        "pass_rate": round(
            pass_rate,
            4,
        ),
        "pass_rate_percent": round(
            pass_rate * 100,
            2,
        ),
        "average_duration_seconds": round(
            mean(durations),
            2,
        ) if durations else 0.0,
        "p95_duration_seconds": round(
            calculate_percentile(
                durations,
                0.95,
            ),
            2,
        ),
        "all_passed": (
            passed_count == total
        ),
    }


def save_json_report(
    report_path: Path,
    report: dict[str, Any],
) -> None:
    """
    保存完整 JSON 报告。
    """

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )


def save_csv_report(
    report_path: Path,
    results: list[dict[str, Any]],
) -> None:
    """
    保存适合快速查看的 CSV 报告。
    """

    fieldnames = [
        "id",
        "name",
        "passed",
        "actual_status",
        "duration_seconds",
        "missing_keywords",
        "missing_symbols",
        "found_forbidden_phrases",
        "error",
    ]

    with report_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    "id": result["id"],
                    "name": result["name"],
                    "passed": result["passed"],
                    "actual_status": (
                        result["actual_status"]
                    ),
                    "duration_seconds": (
                        result[
                            "duration_seconds"
                        ]
                    ),
                    "missing_keywords": "|".join(
                        result[
                            "missing_keywords"
                        ]
                    ),
                    "missing_symbols": "|".join(
                        result[
                            "missing_symbols"
                        ]
                    ),
                    "found_forbidden_phrases": (
                        "|".join(
                            result[
                                "found_forbidden_phrases"
                            ]
                        )
                    ),
                    "error": (
                        result["error"] or ""
                    ),
                }
            )


def print_case_result(
    result: dict[str, Any],
) -> None:
    """
    在终端打印单个测试结果。
    """

    status_mark = (
        "通过"
        if result["passed"]
        else "失败"
    )

    print(
        f"\n[{status_mark}] "
        f"{result['id']}："
        f"{result['name']}"
    )

    print(
        "  返回状态："
        f"{result['actual_status']}"
    )

    print(
        "  客户端耗时："
        f"{result['duration_seconds']} 秒"
    )

    if result["error"]:
        print(
            f"  错误：{result['error']}"
        )
        return

    if result["missing_keywords"]:
        print(
            "  缺少关键词："
            + "、".join(
                result["missing_keywords"]
            )
        )

    if result["missing_symbols"]:
        print(
            "  缺少源码符号："
            + "、".join(
                result["missing_symbols"]
            )
        )

    if result[
        "missing_source_keywords"
    ]:
        print(
            "  数据来源缺少："
            + "、".join(
                result[
                    "missing_source_keywords"
                ]
            )
        )

    if result[
        "found_forbidden_phrases"
    ]:
        print(
            "  出现未完成短语："
            + "、".join(
                result[
                    "found_forbidden_phrases"
                ]
            )
        )

    failed_checks = [
        check_name
        for check_name, passed
        in result["checks"].items()
        if not passed
    ]

    if failed_checks:
        print(
            "  未通过检查："
            + "、".join(
                failed_checks
            )
        )


def main() -> None:
    """
    执行全部测试用例并生成评估报告。
    """

    parser = argparse.ArgumentParser(
        description=(
            "评估 real-code-analyst "
            "A2A 服务。"
        )
    )

    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:5001",
        help="远程 A2A Agent 地址。",
    )

    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASE_FILE,
        help="测试用例 JSON 文件。",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="单次请求最大等待秒数。",
    )

    args = parser.parse_args()

    test_cases = load_test_cases(
        args.cases
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 72)
    print("最小 Agent 评估系统")
    print("=" * 72)
    print(f"服务地址：{args.endpoint}")
    print(f"测试用例：{args.cases}")
    print(f"用例数量：{len(test_cases)}")
    print(
        "执行方式：串行执行，"
        "避免与服务端 AGENT_LOCK 冲突。"
    )

    results: list[dict[str, Any]] = []

    for index, case in enumerate(
        test_cases,
        start=1,
    ):
        print("\n" + "-" * 72)
        print(
            f"正在执行 {index}/"
            f"{len(test_cases)}："
            f"{case['id']}"
        )
        print("-" * 72)
        print(f"问题：{case['question']}")

        started_at = time.perf_counter()

        try:
            result, duration = (
                call_remote_agent(
                    endpoint=args.endpoint,
                    question=case["question"],
                    timeout=args.timeout,
                )
            )

            evaluation_result = (
                evaluate_result(
                    case=case,
                    result=result,
                    duration=duration,
                )
            )

        except Exception as exc:
            duration = (
                time.perf_counter()
                - started_at
            )

            evaluation_result = (
                create_error_result(
                    case=case,
                    exc=exc,
                    duration=duration,
                )
            )

        results.append(
            evaluation_result
        )

        print_case_result(
            evaluation_result
        )

    summary = build_summary(
        results
    )

    generated_at = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    report = {
        "generated_at": generated_at,
        "endpoint": args.endpoint,
        "case_file": str(
            args.cases.resolve()
        ),
        "summary": summary,
        "results": results,
    }

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    json_report_path = (
        RESULTS_DIR
        / f"evaluation_{timestamp}.json"
    )

    csv_report_path = (
        RESULTS_DIR
        / f"evaluation_{timestamp}.csv"
    )

    save_json_report(
        json_report_path,
        report,
    )

    save_csv_report(
        csv_report_path,
        results,
    )

    print("\n" + "=" * 72)
    print("评估汇总")
    print("=" * 72)
    print(
        f"测试总数："
        f"{summary['total_cases']}"
    )
    print(
        f"通过数量："
        f"{summary['passed_cases']}"
    )
    print(
        f"失败数量："
        f"{summary['failed_cases']}"
    )
    print(
        f"通过率："
        f"{summary['pass_rate_percent']}%"
    )
    print(
        "平均耗时："
        f"{summary['average_duration_seconds']} 秒"
    )
    print(
        "P95 耗时："
        f"{summary['p95_duration_seconds']} 秒"
    )
    print(
        f"JSON 报告：{json_report_path}"
    )
    print(
        f"CSV 报告：{csv_report_path}"
    )

    if summary["all_passed"]:
        print("\n评估结论：全部测试通过。")
    else:
        print(
            "\n评估结论：存在失败用例，"
            "请查看报告中的失败原因。"
        )


if __name__ == "__main__":
    main()