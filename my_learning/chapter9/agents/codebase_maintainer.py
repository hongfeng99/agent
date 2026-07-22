import re
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from context import ContextBuilder, ContextConfig, ContextPacket
from integrations import NoteContextAdapter, TerminalContextAdapter
from tools import NoteTool, TerminalTool


class LLMProtocol(Protocol):
    """
    CodebaseMaintainer 所需要的大模型接口。

    只要一个对象提供：

        invoke(prompt: str) -> str

    就可以作为 CodebaseMaintainer 的大模型。
    """

    def invoke(self, prompt: str) -> str:
        ...


class CodebaseMaintainer:
    """
    长程代码库维护助手。

    负责整合：

    1. TerminalTool：即时探索代码；
    2. NoteTool：保存长期项目状态；
    3. ContextBuilder：筛选并组织上下文；
    4. LLM：基于最终上下文生成回答；
    5. conversation_history：保存当前会话历史。
    """

    SUPPORTED_MODES = {
        "auto",
        "explore",
        "analyze",
        "plan",
    }

    MODE_DESCRIPTIONS = {
        "auto": (
            "根据用户问题自动选择合适的代码探索信息，"
            "并结合历史笔记回答。"
        ),
        "explore": (
            "重点探索项目结构、文件分布和模块职责。"
        ),
        "analyze": (
            "重点分析代码实现、潜在问题、TODO、FIXME"
            "以及可维护性。"
        ),
        "plan": (
            "重点结合已有笔记制定后续任务计划，"
            "避免无目的地读取大量代码。"
        ),
    }

    def __init__(
        self,
        project_name: str,
        codebase_path: str | Path,
        llm: LLMProtocol,
        notes_workspace: str | Path | None = None,
        focus_path: str = ".",
        memory_tool: Any | None = None,
    ) -> None:
        """
        初始化代码库维护助手。

        project_name:
            当前项目名称。

        codebase_path:
            TerminalTool 可以访问的代码库根目录。

        llm:
            提供 invoke(prompt) 方法的大模型对象。

        notes_workspace:
            NoteTool 保存笔记的目录。

        focus_path:
            默认重点探索的相对目录。

        memory_tool:
            可选的 Chapter 8 记忆工具。
            当前第一版可以先不传。
        """

        if not isinstance(project_name, str):
            raise TypeError(
                "project_name 必须是字符串。"
            )

        project_name = project_name.strip()

        if not project_name:
            raise ValueError(
                "project_name 不能为空。"
            )

        if not hasattr(llm, "invoke"):
            raise TypeError(
                "llm 必须提供 invoke(prompt) 方法。"
            )

        self.project_name = project_name
        self.codebase_path = Path(
            codebase_path
        ).resolve()

        self.focus_path = focus_path
        self.llm = llm

        self.session_id = (
            "session_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        if notes_workspace is None:
            notes_workspace = (
                self.codebase_path
                / ".agent_notes"
                / project_name
            )

        # 1. 初始化基础工具。
        self.note_tool = NoteTool(
            workspace=notes_workspace
        )

        self.terminal_tool = TerminalTool(
            workspace=self.codebase_path,
            max_output_chars=15_000,
            max_file_size=1_000_000,
        )

        # 2. 初始化上下文构建器。
        self.context_builder = ContextBuilder(
            memory_tool=memory_tool,
            rag_tool=None,
            config=ContextConfig(
                max_tokens=2500,
                reserve_ratio=0.15,
                min_relevance=0.1,
                enable_compression=True,
                relevance_weight=0.7,
                recency_weight=0.3,
            ),
        )

        # 3. 初始化适配器。
        self.note_adapter = NoteContextAdapter(
            note_tool=self.note_tool,
            context_builder=self.context_builder,
        )

        self.terminal_adapter = (
            TerminalContextAdapter(
                terminal_tool=self.terminal_tool,
                context_builder=self.context_builder,
            )
        )

        # 4. 当前会话历史。
        self.conversation_history: list[
            dict[str, Any]
        ] = []

        # 5. 运行统计。
        self.stats = {
            "session_start": datetime.now(),
            "runs": 0,
            "terminal_packets": 0,
            "notes_created": 0,
            "issues_found": 0,
            "duplicate_notes_skipped": 0,
        }




    def _build_system_instructions(
        self,
        mode: str,
    ) -> str:
        """
        根据运行模式生成系统指令。
        """

        mode_description = (
            self.MODE_DESCRIPTIONS[mode]
        )

        return f"""
            你是一位 Python 代码库维护助手。

            当前项目：{self.project_name}
            当前模式：{mode}
            模式要求：{mode_description}

            请遵守以下规则：

            1. 只根据提供的代码、笔记和对话历史回答；
            2. 没有看到真实代码时，不要假装已经读取；
            3. 明确区分代码事实、合理推断和改进建议；
            4. 发现问题时说明文件位置和原因；
            5. 给出下一步行动时，应具体、可执行；
            6. 不要编造不存在的文件、类或函数；
            7. 回答应优先解决用户当前问题。
            """.strip()
    



    def _extract_search_term(
        self,
        user_input: str,
    ) -> str | None:
        """
        从用户问题中提取可能的代码搜索词。

        优先提取：

        1. Python 文件路径；
        2. 类名、函数名等英文标识符。
        """

        # 匹配 builder.py 或 context/builder.py。
        file_match = re.search(
            r"[\w./\\-]+\.py",
            user_input,
        )

        if file_match:
            return file_match.group(0).replace(
                "\\",
                "/",
            )

        identifiers = re.findall(
            r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b",
            user_input,
        )

        ignored_words = {
            "python",
            "chapter",
            "agent",
            "auto",
            "explore",
            "analyze",
            "plan",
            "todo",
            "fixme",
        }

        candidates = [
            identifier
            for identifier in identifiers
            if identifier.lower()
            not in ignored_words
        ]

        if not candidates:
            return None

        # 较长的标识符往往更具体。
        return max(
            candidates,
            key=len,
        )
    




    def _collect_terminal_packets(
        self,
        user_input: str,
        mode: str,
    ) -> list[ContextPacket]:
        """
        根据运行模式收集即时代码上下文。

        当前采用两阶段检索：

        1. 搜索符号或关键词；
        2. 自动读取搜索命中位置附近的源码。
        """

        packets: list[ContextPacket] = []

        search_term = self._extract_search_term(
            user_input
        )

        # explore 模式总是查看目录结构。
        #
        # auto 模式只有在没有提取到明确代码符号时，
        # 才优先查看目录树，避免目录树挤占源码预算。
        if (
            mode == "explore"
            or (
                mode == "auto"
                and search_term is None
            )
        ):
            packets.append(
                self.terminal_adapter
                .collect_structure(
                    path=self.focus_path,
                    max_depth=2,
                )
            )

        # analyze 和 auto 模式读取具体代码。
        if mode in {"analyze", "auto"}:
            if search_term:
                # 用户直接给出了 Python 文件路径。
                if search_term.endswith(".py"):
                    try:
                        packets.append(
                            self.terminal_adapter
                            .collect_file(
                                path=search_term,
                                start_line=1,
                                end_line=180,
                            )
                        )
                    except (
                        FileNotFoundError,
                        PermissionError,
                        ValueError,
                        OSError,
                    ):
                        packets.extend(
                            self.terminal_adapter
                            .collect_search_context(
                                query=search_term,
                                path=self.focus_path,
                                max_results=20,
                                max_matches=2,
                                context_lines=30,
                            )
                        )

                else:
                    # ContextBuilder 这样的首字母大写标识符，
                    # 优先搜索类定义，而不是所有引用位置。
                    if re.fullmatch(
                        r"[A-Z][A-Za-z0-9_]*",
                        search_term,
                    ):
                        code_query = (
                            f"class {search_term}"
                        )
                    else:
                        code_query = search_term

                    packets.extend(
                        self.terminal_adapter
                        .collect_search_context(
                            query=code_query,
                            path=self.focus_path,
                            max_results=20,
                            max_matches=2,
                            context_lines=35,
                        )
                    )

        # 用户明确询问 GSSC 时，
        # 分别读取四个阶段和统一入口的真实代码。
        if "gssc" in user_input.lower():
            method_queries = [
                "def _gather",
                "def _select",
                "def _structure",
                "def _compress",
                "def build",
            ]

            for method_query in method_queries:
                method_packets = (
                    self.terminal_adapter
                    .collect_search_context(
                        query=method_query,
                        path=self.focus_path,
                        max_results=5,
                        max_matches=1,
                        context_lines=18,
                    )
                )

                packets.extend(method_packets)

        # analyze 模式额外检查 TODO 和 FIXME。
        if mode == "analyze":
            packets.append(
                self.terminal_adapter
                .collect_search(
                    query="TODO",
                    path=self.focus_path,
                    max_results=20,
                )
            )

            packets.append(
                self.terminal_adapter
                .collect_search(
                    query="FIXME",
                    path=self.focus_path,
                    max_results=20,
                )
            )

        # 对重复的信息包进行去重。
        deduplicated_packets: list[
            ContextPacket
        ] = []

        seen_keys: set[tuple[Any, ...]] = set()

        for packet in packets:
            metadata = packet.metadata or {}

            packet_key = (
                metadata.get("type"),
                metadata.get("path"),
                metadata.get("query"),
                metadata.get("start_line"),
                metadata.get("end_line"),
            )

            if packet_key in seen_keys:
                continue

            seen_keys.add(packet_key)
            deduplicated_packets.append(packet)

        self.stats["terminal_packets"] += len(
            deduplicated_packets
        )

        return deduplicated_packets




    def _collect_note_packets(
        self,
        user_input: str,
    ) -> list[ContextPacket]:
        """
        从 NoteTool 检索相关笔记并转换为 ContextPacket。
        """

        search_term = self._extract_search_term(
            user_input
        )

        note_query = (
            search_term
            if search_term
            else user_input
        )

        notes = (
            self.note_adapter
            .retrieve_relevant_notes(
                query=note_query,
                limit=3,
                blocker_limit=1,
            )
        )

        return self.note_adapter.notes_to_packets(
            notes
        )
    


    def _build_auto_note_tag(
        self,
        user_input: str,
        note_type: str,
    ) -> str:
        """
        根据用户问题和笔记类型生成稳定的唯一标签。

        同一个问题、同一种笔记类型会得到相同标签，
        用于避免重复创建自动笔记。
        """

        raw_text = (
            f"{self.project_name}|"
            f"{note_type}|"
            f"{user_input.strip().lower()}"
        )

        digest = hashlib.sha1(
            raw_text.encode("utf-8")
        ).hexdigest()[:12]

        return f"auto_key_{digest}"



    def _auto_note_exists(
        self,
        auto_tag: str,
    ) -> bool:
        """
        检查是否已经存在相同的自动笔记。
        """

        existing_notes = self.note_tool.run({
            "action": "list",
            "tags": [auto_tag],
            "limit": 1,
        })

        return bool(existing_notes)



    def _postprocess_response(
        self,
        user_input: str,
        response: str,
        mode: str,
    ) -> list[str]:
        """
        分析模型回答，自动保存重要项目笔记。

        当前规则：

        1. 回答明确包含问题、错误或阻塞信息：
           创建 blocker 笔记；

        2. 用户询问计划、任务或下一步，
           或当前处于 plan 模式：
           创建 action 笔记；

        3. 同一个问题不会重复创建同类型笔记。

        返回：
            本轮新创建的笔记 ID 列表。
        """

        if not isinstance(user_input, str):
            raise TypeError(
                "user_input 必须是字符串。"
            )

        if not isinstance(response, str):
            raise TypeError(
                "response 必须是字符串。"
            )

        response_lower = response.lower()
        input_lower = user_input.lower()

        issue_keywords = {
            "问题",
            "错误",
            "bug",
            "阻塞",
            "缺陷",
            "失败",
            "风险",
            "未实现",
            "缺少",
        }

        planning_keywords = {
            "计划",
            "下一步",
            "任务",
            "todo",
            "待办",
            "怎么做",
            "如何实现",
        }

        has_issue = any(
            keyword in response_lower
            for keyword in issue_keywords
        )

        is_planning = (
            mode == "plan"
            or any(
                keyword in input_lower
                for keyword in planning_keywords
            )
        )

        created_note_ids: list[str] = []

        # 优先记录明确发现的问题。
        if has_issue:
            note_type = "blocker"

            auto_tag = self._build_auto_note_tag(
                user_input=user_input,
                note_type=note_type,
            )

            if self._auto_note_exists(auto_tag):
                self.stats[
                    "duplicate_notes_skipped"
                ] += 1

                print(
                    "[CodebaseMaintainer] "
                    "相同问题笔记已存在，跳过创建。"
                )

                return created_note_ids

            title_text = (
                user_input[:40].strip()
                or "未命名问题"
            )

            note_id = self.note_tool.run({
                "action": "create",
                "title": (
                    f"发现问题：{title_text}"
                ),
                "content": (
                    "## 用户问题\n\n"
                    f"{user_input}\n\n"
                    "## 问题分析\n\n"
                    f"{response[:1500]}"
                ),
                "note_type": "blocker",
                "tags": [
                    self.project_name,
                    "auto_detected",
                    self.session_id,
                    auto_tag,
                ],
            })

            created_note_ids.append(note_id)

            self.stats["notes_created"] += 1
            self.stats["issues_found"] += 1

            print(
                "[CodebaseMaintainer] "
                f"已自动创建 blocker 笔记：{note_id}"
            )

        # 没有明确问题时，再判断是否属于任务规划。
        elif is_planning:
            note_type = "action"

            auto_tag = self._build_auto_note_tag(
                user_input=user_input,
                note_type=note_type,
            )

            if self._auto_note_exists(auto_tag):
                self.stats[
                    "duplicate_notes_skipped"
                ] += 1

                print(
                    "[CodebaseMaintainer] "
                    "相同行动计划已存在，跳过创建。"
                )

                return created_note_ids

            title_text = (
                user_input[:40].strip()
                or "未命名任务"
            )

            note_id = self.note_tool.run({
                "action": "create",
                "title": (
                    f"行动计划：{title_text}"
                ),
                "content": (
                    "## 用户需求\n\n"
                    f"{user_input}\n\n"
                    "## 行动计划\n\n"
                    f"{response[:1500]}"
                ),
                "note_type": "action",
                "tags": [
                    self.project_name,
                    "planning",
                    self.session_id,
                    auto_tag,
                ],
            })

            created_note_ids.append(note_id)

            self.stats["notes_created"] += 1

            print(
                "[CodebaseMaintainer] "
                f"已自动创建 action 笔记：{note_id}"
            )

        return created_note_ids



    def run(
        self,
        user_input: str,
        mode: str = "auto",
    ) -> str:
        """
        运行一次代码库维护任务。

        流程：

        1. 检查输入；
        2. 使用 TerminalTool 收集即时上下文；
        3. 使用 NoteTool 检索长期笔记；
        4. 使用 ContextBuilder 构建最终上下文；
        5. 调用 LLM；
        6. 更新对话历史。
        """

        if not isinstance(user_input, str):
            raise TypeError(
                "user_input 必须是字符串。"
            )

        user_input = user_input.strip()

        if not user_input:
            raise ValueError(
                "user_input 不能为空。"
            )

        if mode not in self.SUPPORTED_MODES:
            supported = "、".join(
                sorted(self.SUPPORTED_MODES)
            )

            raise ValueError(
                f"不支持的 mode：{mode}。"
                f"当前支持：{supported}。"
            )

        print(
            "\n"
            + "=" * 70
        )

        print(
            f"项目：{self.project_name}"
        )

        print(
            f"模式：{mode}"
        )

        print(
            f"问题：{user_input}"
        )

        print(
            "=" * 70
        )

        # 1. TerminalTool 即时上下文。
        terminal_packets = (
            self._collect_terminal_packets(
                user_input=user_input,
                mode=mode,
            )
        )

        # 2. NoteTool 持久笔记。
        note_packets = (
            self._collect_note_packets(
                user_input=user_input,
            )
        )

        custom_packets = (
            terminal_packets
            + note_packets
        )

        # 3. 构建最终上下文。
        final_context = (
            self.context_builder.build(
                user_query=user_input,
                conversation_history=(
                    self.conversation_history
                ),
                system_instructions=(
                    self._build_system_instructions(
                        mode
                    )
                ),
                custom_packets=custom_packets,
            )
        )

        # 4. 调用 LLM。
        response = self.llm.invoke(
            final_context
        )

        if not isinstance(response, str):
            response = str(response)


        # 5. 分析回答并自动创建项目笔记。
        self._postprocess_response(
            user_input=user_input,
            response=response,
            mode=mode,
        )


        # 5. 保存当前会话历史。
        now = datetime.now()

        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": now,
        })

        self.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now(),
        })

        # 只保留最近 20 条本地历史，
        # ContextBuilder 内部还会进一步选取最近 5 条。
        self.conversation_history = (
            self.conversation_history[-20:]
        )

        self.stats["runs"] += 1

        return response
    




    def explore(
        self,
        user_input: str = "请概述当前代码库结构。",
    ) -> str:
        """
        使用 explore 模式运行。
        """

        return self.run(
            user_input=user_input,
            mode="explore",
        )

    def analyze(
        self,
        user_input: str = "请分析当前代码库中的问题。",
    ) -> str:
        """
        使用 analyze 模式运行。
        """

        return self.run(
            user_input=user_input,
            mode="analyze",
        )

    def plan(
        self,
        user_input: str = "请制定下一阶段的维护计划。",
    ) -> str:
        """
        使用 plan 模式运行。
        """

        return self.run(
            user_input=user_input,
            mode="plan",
        )

    def record_note(
        self,
        title: str,
        content: str,
        note_type: str = "general",
        tags: list[str] | None = None,
    ) -> str:
        """
        手动记录一条项目笔记。
        """

        note_id = self.note_tool.run({
            "action": "create",
            "title": title,
            "content": content,
            "note_type": note_type,
            "tags": tags or [
                self.project_name,
            ],
        })

        self.stats["notes_created"] += 1

        return note_id

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """
        返回当前会话统计。
        """

        duration = (
            datetime.now()
            - self.stats["session_start"]
        ).total_seconds()

        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "duration_seconds": duration,
            "runs": self.stats["runs"],
            "terminal_packets": (
                self.stats["terminal_packets"]
            ),
            "notes_created": (
                self.stats["notes_created"]
            ),
            "history_messages": len(
                self.conversation_history
            ),
            "note_summary": self.note_tool.run({
                "action": "summary",
            }),
            "issues_found": (
                self.stats["issues_found"]
            ),
            "duplicate_notes_skipped": (
                self.stats[
                    "duplicate_notes_skipped"
                ]
            ),
        }
    

    def generate_report(
        self,
        save_to_file: bool = True,
        output_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        生成当前代码库维护会话报告。

        报告包含：

        1. 会话 ID；
        2. 项目名称；
        3. 运行次数；
        4. Terminal 信息包数量；
        5. 自动创建的笔记数量；
        6. 发现的问题数量；
        7. 笔记库统计；
        8. 报告生成时间。

        save_to_file=False 时只返回字典，不写入文件。
        """

        report = self.get_stats()

        report["generated_at"] = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        if not save_to_file:
            return report

        if output_dir is None:
            report_dir = (
                self.note_tool.workspace
                / "reports"
            )
        else:
            report_dir = Path(
                output_dir
            ).resolve()

        report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        report_path = (
            report_dir
            / (
                "maintainer_report_"
                f"{self.session_id}.json"
            )
        )

        report["report_file"] = str(
            report_path
        )

        report_path.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        print(
            "[CodebaseMaintainer] "
            f"会话报告已保存：{report_path}"
        )

        return report


    def explore(
        self,
        user_input: str = "请概述当前代码库结构。",
    ) -> str:
        """
        使用 explore 模式运行。
        """

        return self.run(
            user_input=user_input,
            mode="explore",
        )

    def analyze(
        self,
        user_input: str = "请分析当前代码库中的问题。",
    ) -> str:
        """
        使用 analyze 模式运行。
        """

        return self.run(
            user_input=user_input,
            mode="analyze",
        )

    def plan(
        self,
        user_input: str = "请制定下一阶段的维护计划。",
    ) -> str:
        """
        使用 plan 模式运行。
        """

        return self.run(
            user_input=user_input,
            mode="plan",
        )

    def record_note(
        self,
        title: str,
        content: str,
        note_type: str = "general",
        tags: list[str] | None = None,
    ) -> str:
        """
        手动记录一条项目笔记。
        """

        note_id = self.note_tool.run({
            "action": "create",
            "title": title,
            "content": content,
            "note_type": note_type,
            "tags": tags or [
                self.project_name,
            ],
        })

        self.stats["notes_created"] += 1

        return note_id

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """
        返回当前会话统计。
        """

        duration = (
            datetime.now()
            - self.stats["session_start"]
        ).total_seconds()

        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "duration_seconds": duration,
            "runs": self.stats["runs"],
            "terminal_packets": (
                self.stats["terminal_packets"]
            ),
            "notes_created": (
                self.stats["notes_created"]
            ),
            "history_messages": len(
                self.conversation_history
            ),
            "note_summary": self.note_tool.run({
                "action": "summary",
            }),
        }