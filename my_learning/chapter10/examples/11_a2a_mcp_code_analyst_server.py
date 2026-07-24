import asyncio
import json
import sys
import threading
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.protocols import A2AServer, MCPClient


# 当前文件位于：
#
# hello-agents/
# └── my_learning/
#     └── chapter10/
#         └── examples/
#             └── 11_a2a_mcp_code_analyst_server.py
#
# parents[3] 对应 hello-agents 项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 自定义代码库 MCP Server。
MCP_SERVER_SCRIPT = Path(__file__).with_name(
    "05_codebase_mcp_server.py"
).resolve()

# Chapter 9 目录。
CHAPTER9_DIRECTORY = (
    PROJECT_ROOT
    / "my_learning"
    / "chapter9"
)

# SimpleAgent 可能保存会话状态。
#
# 为避免多个 A2A 请求同时操作同一个 Agent，
# 当前学习版本使用线程锁串行执行模型分析。
AGENT_LOCK = threading.Lock()


def check_environment() -> None:
    """
    检查程序运行所需的文件和目录。
    """

    if not PROJECT_ROOT.exists():
        raise FileNotFoundError(
            f"找不到项目根目录：{PROJECT_ROOT}"
        )

    if not MCP_SERVER_SCRIPT.exists():
        raise FileNotFoundError(
            f"找不到代码库 MCP Server："
            f"{MCP_SERVER_SCRIPT}"
        )

    if not CHAPTER9_DIRECTORY.exists():
        raise FileNotFoundError(
            f"找不到 Chapter 9 目录："
            f"{CHAPTER9_DIRECTORY}"
        )

    env_file = PROJECT_ROOT / ".env"

    if not env_file.exists():
        raise FileNotFoundError(
            f"找不到模型配置文件：{env_file}"
        )


def parse_json_result(
    result: Any,
) -> dict[str, Any]:
    """
    将 MCP 工具返回的 JSON 字符串解析成字典。
    """

    if not isinstance(result, str):
        raise TypeError(
            "预期 MCP 返回字符串，实际得到："
            f"{type(result).__name__}"
        )

    data = json.loads(result)

    if not isinstance(data, dict):
        raise TypeError(
            "预期 MCP 返回的 JSON 顶层是对象。"
        )

    return data


def find_contextbuilder_path(
    search_data: dict[str, Any],
) -> str:
    """
    从 search_symbol 的结果中找到 ContextBuilder 定义文件。

    优先选择内容包含：
        class ContextBuilder
    的搜索结果，而不是导入或使用位置。
    """

    matches = search_data.get("matches", [])

    if not isinstance(matches, list):
        raise TypeError(
            "search_symbol 返回的 matches 不是列表。"
        )

    for match in matches:
        if not isinstance(match, dict):
            continue

        content = str(
            match.get("content", "")
        )

        path = str(
            match.get("path", "")
        )

        if (
            "class ContextBuilder" in content
            and path.endswith(".py")
        ):
            return path

    raise LookupError(
        "搜索结果中没有找到 ContextBuilder 的类定义。"
    )


async def collect_contextbuilder_source() -> tuple[
    str,
    list[str],
]:
    """
    通过 MCP 精确收集 ContextBuilder 的关键源码。

    这里由 Python 明确控制读取过程：

    1. 搜索 ContextBuilder；
    2. 找到类定义文件；
    3. 精确读取 build；
    4. 精确读取 Gather、Select、Structure、Compress；
    5. 将结果组合成源码上下文。

    不再依赖大模型自行决定是否继续翻页。
    """

    client = MCPClient(
        [
            sys.executable,
            str(MCP_SERVER_SCRIPT),
        ]
    )

    # 每个阶段对应的候选方法名。
    #
    # 首选带下划线的内部方法；
    # 如果项目使用公开方法名，也可以自动尝试。
    symbol_groups = [
        (
            "Build 入口",
            [
                "ContextBuilder.build",
            ],
        ),
        (
            "Gather 阶段",
            [
                "ContextBuilder._gather",
                "ContextBuilder.gather",
            ],
        ),
        (
            "Select 阶段",
            [
                "ContextBuilder._select",
                "ContextBuilder.select",
            ],
        ),
        (
            "Structure 阶段",
            [
                "ContextBuilder._structure",
                "ContextBuilder.structure",
            ],
        ),
        (
            "Compress 阶段",
            [
                "ContextBuilder._compress",
                "ContextBuilder.compress",
            ],
        ),
    ]

    source_sections: list[str] = []
    symbols_read: list[str] = []

    async with client:
        print(
            "[MCP] 正在搜索 ContextBuilder……",
            flush=True,
        )

        search_result = await client.call_tool(
            "search_symbol",
            {
                "keyword": "ContextBuilder",
                "relative_directory": (
                    "my_learning/chapter9"
                ),
                "max_results": 30,
            },
        )

        search_data = parse_json_result(
            search_result
        )

        source_path = find_contextbuilder_path(
            search_data
        )

        print(
            f"[MCP] 找到类定义文件：{source_path}",
            flush=True,
        )

        source_sections.append(
            "# ContextBuilder 搜索定位结果\n"
            f"定义文件：{source_path}\n\n"
            + json.dumps(
                search_data,
                ensure_ascii=False,
                indent=2,
            )
        )

        for stage_name, candidates in symbol_groups:
            last_error: Exception | None = None
            selected_symbol: str | None = None
            selected_content: str | None = None

            for symbol in candidates:
                try:
                    print(
                        f"[MCP] 尝试读取：{symbol}",
                        flush=True,
                    )

                    symbol_result = await client.call_tool(
                        "read_python_symbol",
                        {
                            "path": source_path,
                            "symbol": symbol,
                        },
                    )

                    symbol_data = parse_json_result(
                        symbol_result
                    )

                    content = symbol_data.get(
                        "content"
                    )

                    if not isinstance(content, str):
                        raise TypeError(
                            f"{symbol} 返回的 content "
                            "不是字符串。"
                        )

                    if not content.strip():
                        raise ValueError(
                            f"{symbol} 返回的源码为空。"
                        )

                    selected_symbol = symbol
                    selected_content = content
                    break

                except Exception as exc:
                    last_error = exc

            if (
                selected_symbol is None
                or selected_content is None
            ):
                raise LookupError(
                    f"无法读取 {stage_name} 对应的方法。"
                    f"尝试过：{candidates}。"
                    f"最后错误：{last_error}"
                )

            symbols_read.append(selected_symbol)

            source_sections.append(
                f"# {stage_name}\n"
                f"符号：{selected_symbol}\n\n"
                f"{selected_content}"
            )

            print(
                f"[MCP] 成功读取：{selected_symbol}",
                flush=True,
            )

    source_context = "\n\n".join(
        source_sections
    )

    return source_context, symbols_read


def create_code_analysis_agent() -> SimpleAgent:
    """
    创建只负责分析源码的内部 Agent。

    源码已经由 Python 通过 MCP 收集完成，
    因此该 Agent 不再负责搜索和读取工具调用。
    """

    load_dotenv(PROJECT_ROOT / ".env")

    llm = HelloAgentsLLM()

    return SimpleAgent(
        name="远程代码分析专家",
        llm=llm,
        system_prompt="""
你是一名严谨的 Python 代码分析专家。

用户会向你提供通过 MCP Server 从真实项目中读取的源码。

你必须遵守以下要求：

1. 只能根据提供的真实源码进行分析；
2. 不得编造没有出现在源码中的实现；
3. 明确区分：
   - 代码中已经实现的内容；
   - 根据源码作出的合理推断；
   - 当前代码尚未实现的内容；
4. 最终使用中文回答；
5. 最终回答必须完整包含：
   - ContextBuilder 的主要职责；
   - Gather 阶段；
   - Select 阶段；
   - Structure 阶段；
   - Compress 阶段；
   - 每个阶段调用的主要方法；
   - 当前实现的局限；
   - 简要总结；
6. 不要回答“还需要继续读取源码”；
7. 关键源码已经全部提供，不需要调用任何工具；
8. 如果某项不能从源码中确认，应明确说明无法确认；
9. 不要把搜索结果中的导入语句误认为类定义；
10. 描述执行流程时，应说明数据如何从一个阶段传递到下一个阶段。
""".strip(),
    )


def build_analysis_question(
    task: str,
    source_context: str,
) -> str:
    """
    构造最终发送给内部分析 Agent 的问题。
    """

    return f"""
请完成下面的代码分析任务：

{task}

以下内容是通过 MCP Server 从
my_learning/chapter9 的真实代码中精确读取的源码。

================ 真实源码开始 ================

{source_context}

================ 真实源码结束 ================

请仅根据以上源码进行分析。

最终回答必须使用下面的结构：

一、ContextBuilder 的主要职责

二、GSSC 总体执行流程

三、Gather 阶段
- 对应方法；
- 输入；
- 主要处理；
- 输出。

四、Select 阶段
- 对应方法；
- 输入；
- 主要处理；
- 输出。

五、Structure 阶段
- 对应方法；
- 输入；
- 主要处理；
- 输出。

六、Compress 阶段
- 对应方法；
- 输入；
- 主要处理；
- 输出。

七、主要方法及调用关系

八、当前实现的局限

九、总结

不要回答“需要继续读取代码”。
不要重新制定计划，直接输出完整分析。
""".strip()


def evaluate_analysis(
    analysis: str,
) -> tuple[str, list[str]]:
    """
    检查分析结果是否完整。

    返回：
        status:
            completed 或 incomplete。

        reasons:
            完整性检查不通过的原因。
    """

    reasons: list[str] = []

    required_stage_keywords = {
        "Gather": (
            "Gather",
            "gather",
            "收集阶段",
        ),
        "Select": (
            "Select",
            "select",
            "选择阶段",
        ),
        "Structure": (
            "Structure",
            "structure",
            "结构化阶段",
        ),
        "Compress": (
            "Compress",
            "compress",
            "压缩阶段",
        ),
    }

    for stage, keywords in (
        required_stage_keywords.items()
    ):
        if not any(
            keyword in analysis
            for keyword in keywords
        ):
            reasons.append(
                f"最终分析缺少 {stage} 阶段。"
            )

    failure_markers = (
        "还需要继续读取",
        "需要继续读取",
        "继续读取源码",
        "路径可能有误",
        "无法读取源码",
        "未能读取源码",
        "没有读取到真实代码",
        "分析尚未完成",
        "无法完成分析",
    )

    found_failure_markers = [
        marker
        for marker in failure_markers
        if marker in analysis
    ]

    if found_failure_markers:
        reasons.append(
            "最终回答仍包含未完成标志："
            + "、".join(found_failure_markers)
        )

    minimum_length = 500

    if len(analysis.strip()) < minimum_length:
        reasons.append(
            f"分析内容过短，少于 "
            f"{minimum_length} 个字符。"
        )

    status = (
        "completed"
        if not reasons
        else "incomplete"
    )

    return status, reasons


def create_a2a_server(
    analysis_agent: SimpleAgent,
) -> A2AServer:
    """
    创建对外提供真实代码分析能力的 A2A Server。
    """

    server = A2AServer(
        name="real-code-analyst",
        description=(
            "通过 MCP 精确读取真实项目代码，"
            "并完成代码分析的专业 Agent"
        ),
        version="1.0.0",
    )

    @server.skill("analyze")
    def analyze_code(text: str) -> str:
        """
        接收其他 Agent 委托的代码分析任务。
        """

        started_at = perf_counter()

        task = text.strip()

        # 兼容传入：
        #
        # analyze ContextBuilder ...
        if task.lower().startswith("analyze "):
            task = task[8:].strip()

        if not task:
            return json.dumps(
                {
                    "agent": "real-code-analyst",
                    "status": "failed",
                    "error": "代码分析任务不能为空。",
                },
                ensure_ascii=False,
                indent=2,
            )

        print(
            "\n" + "=" * 72,
            flush=True,
        )
        print(
            f"[A2A] 收到代码分析任务：{task}",
            flush=True,
        )
        print(
            "=" * 72,
            flush=True,
        )

        try:
            print(
                "[A2A] 开始通过 MCP "
                "收集 ContextBuilder 关键源码……",
                flush=True,
            )

            source_context, symbols_read = (
                asyncio.run(
                    collect_contextbuilder_source()
                )
            )

            print(
                "[A2A] MCP 源码收集完成。",
                flush=True,
            )
            print(
                f"[A2A] 共读取 {len(symbols_read)} "
                "个关键方法。",
                flush=True,
            )

            question = build_analysis_question(
                task=task,
                source_context=source_context,
            )

            print(
                "[A2A] 开始调用内部分析 Agent……",
                flush=True,
            )

            # 内部 Agent 不再调用工具，
            # 只根据已经准备好的源码进行一次分析。
            with AGENT_LOCK:
                analysis = analysis_agent.run(
                    question
                )

            if not isinstance(analysis, str):
                analysis = str(analysis)

            status, validation_reasons = (
                evaluate_analysis(analysis)
            )

            elapsed = perf_counter() - started_at

            result = {
                "agent": "real-code-analyst",
                "status": status,
                "task": task,
                "analysis": analysis,
                "data_source": (
                    "通过 MCP Server 精确读取 "
                    "my_learning/chapter9 中 "
                    "ContextBuilder 的关键方法"
                ),
                "symbols_read": symbols_read,
                "elapsed_seconds": round(
                    elapsed,
                    2,
                ),
                "validation": {
                    "passed": (
                        status == "completed"
                    ),
                    "reasons": validation_reasons,
                },
            }

            print(
                f"[A2A] 分析结束，状态：{status}",
                flush=True,
            )
            print(
                f"[A2A] 总耗时：{elapsed:.1f} 秒",
                flush=True,
            )

            if validation_reasons:
                print(
                    "[A2A] 完整性检查未通过：",
                    flush=True,
                )

                for reason in validation_reasons:
                    print(
                        f"  - {reason}",
                        flush=True,
                    )

        except Exception as exc:
            elapsed = perf_counter() - started_at

            print(
                "[A2A] 代码分析任务执行失败。",
                flush=True,
            )
            print(
                f"[A2A] 错误类型："
                f"{type(exc).__name__}",
                flush=True,
            )
            print(
                f"[A2A] 错误信息：{exc}",
                flush=True,
            )
            print(
                f"[A2A] 失败前耗时："
                f"{elapsed:.1f} 秒",
                flush=True,
            )

            result = {
                "agent": "real-code-analyst",
                "status": "failed",
                "task": task,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "elapsed_seconds": round(
                    elapsed,
                    2,
                ),
            }

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    return server


def main() -> None:
    """
    启动 A2A + MCP 真实代码分析服务。
    """

    check_environment()

    print("=" * 72)
    print("Chapter 10：A2A + MCP 真实代码分析服务")
    print("=" * 72)
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"Chapter 9：{CHAPTER9_DIRECTORY}")
    print(f"MCP Server：{MCP_SERVER_SCRIPT}")

    print("\n正在创建内部代码分析 Agent……")
    analysis_agent = create_code_analysis_agent()

    print("正在创建 A2A Server……")
    server = create_a2a_server(
        analysis_agent
    )

    host = "127.0.0.1"
    port = 5001

    print("\n" + "=" * 72)
    print("服务启动信息")
    print("=" * 72)
    print("Agent 名称：real-code-analyst")
    print(f"服务地址：http://{host}:{port}")
    print("可用技能：analyze")
    print("执行流程：")
    print("  1. A2A 接收远程代码分析任务；")
    print("  2. Python 通过 MCP 搜索 ContextBuilder；")
    print("  3. MCP 精确读取 GSSC 关键方法；")
    print("  4. LLM 根据真实源码生成分析；")
    print("  5. A2A 返回结构化结果。")
    print("按 Ctrl + C 停止服务")
    print("=" * 72)

    server.run(
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()