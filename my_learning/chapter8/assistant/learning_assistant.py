import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.memory_tool import MemoryTool
from tools.rag_tool import RAGTool


class LearningAssistant:
    """
    基于 MemoryTool 和 RAGTool 的学习助手。

    负责：

    1. 加载学习文档；
    2. 根据文档回答问题；
    3. 保存学习笔记；
    4. 回顾历史学习记录；
    5. 统计当前学习会话；
    6. 生成 JSON 学习报告。
    """

    def __init__(
        self,
        memory_tool: MemoryTool,
        rag_tool: RAGTool,
        report_dir: str | Path,
        user_id: str = "default_user",
    ) -> None:
        """
        memory_tool:
            已经初始化好的 MemoryTool。

        rag_tool:
            已经初始化好的 RAGTool。

        report_dir:
            学习报告保存目录。

        user_id:
            当前用户编号。
        """

        if not isinstance(memory_tool, MemoryTool):
            raise TypeError(
                "memory_tool 必须是 MemoryTool 对象。"
            )

        if not isinstance(rag_tool, RAGTool):
            raise TypeError(
                "rag_tool 必须是 RAGTool 对象。"
            )

        if not isinstance(user_id, str):
            raise TypeError(
                "user_id 必须是字符串。"
            )

        user_id = user_id.strip()

        if not user_id:
            raise ValueError(
                "user_id 不能为空。"
            )

        self.memory_tool = memory_tool
        self.rag_tool = rag_tool
        self.user_id = user_id

        self.session_id = (
            "session_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        self.session_start = datetime.now()

        self.report_dir = Path(
            report_dir
        ).resolve()

        self.report_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # 当前会话加载过的文档名称
        self.current_documents: list[str] = []

        # 当前会话统计
        self.stats = {
            "documents_loaded": 0,
            "questions_asked": 0,
            "notes_added": 0,
        }

    @staticmethod
    def _parse_tool_result(
        result: Any,
    ) -> dict[str, Any]:
        """
        将工具返回结果统一转换为字典。

        当前 MemoryTool 和 RAGTool
        通常返回 JSON 字符串。
        """

        if isinstance(result, dict):
            return result

        if not isinstance(result, str):
            return {
                "success": False,
                "error": (
                    "工具返回了不支持的数据类型："
                    f"{type(result).__name__}"
                ),
            }

        try:
            parsed_result = json.loads(result)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "工具没有返回合法 JSON。",
                "raw_result": result,
            }

        if not isinstance(parsed_result, dict):
            return {
                "success": False,
                "error": "工具返回的 JSON 不是对象。",
                "raw_result": parsed_result,
            }

        return parsed_result

    def _record_memory(
        self,
        content: str,
        memory_type: str,
        importance: float,
    ) -> dict[str, Any]:
        """
        将内容写入记忆系统。
        """

        result = self.memory_tool.execute(
            "add",
            content=content,
            memory_type=memory_type,
            importance=importance,
        )

        return self._parse_tool_result(
            result
        )

    def load_document(
        self,
        file_path: str | Path,
    ) -> dict[str, Any]:
        """
        将 txt 或 md 文档加载到 RAG 知识库。
        """

        path = Path(file_path).resolve()

        if not path.exists():
            return {
                "success": False,
                "message": f"文件不存在：{path}",
            }

        if not path.is_file():
            return {
                "success": False,
                "message": f"路径不是文件：{path}",
            }

        start_time = datetime.now()

        tool_result = self.rag_tool.execute(
            "add_file",
            file_path=str(path),
        )

        result = self._parse_tool_result(
            tool_result
        )

        if not result.get("success", False):
            return {
                "success": False,
                "message": "文档加载失败。",
                "tool_result": result,
            }

        process_seconds = (
            datetime.now() - start_time
        ).total_seconds()

        self.current_documents.append(
            path.name
        )

        self.stats[
            "documents_loaded"
        ] += 1

        memory_result = self._record_memory(
            content=(
                f"在会话 {self.session_id} 中"
                f"加载了学习文档《{path.name}》。"
            ),
            memory_type="episodic",
            importance=0.9,
        )

        return {
            "success": True,
            "message": (
                f"文档《{path.name}》加载成功。"
            ),
            "process_seconds": round(
                process_seconds,
                3,
            ),
            "rag_result": result,
            "memory_result": memory_result,
        }

    def ask(
        self,
        question: str,
        top_k: int = 3,
        min_score: float = 0.01,
    ) -> dict[str, Any]:
        """
        根据已经加载的文档回答问题。
        """

        if not isinstance(question, str):
            raise TypeError(
                "question 必须是字符串。"
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "question 不能为空。"
            )

        if not self.current_documents:
            return {
                "success": False,
                "message": (
                    "当前会话尚未加载文档，"
                    "请先调用 load_document()。"
                ),
            }

        # 用户当前的问题属于当前任务上下文，
        # 因此先写入工作记忆。
        self._record_memory(
            content=f"用户提问：{question}",
            memory_type="working",
            importance=0.6,
        )

        tool_result = self.rag_tool.execute(
            "ask",
            question=question,
            top_k=top_k,
            min_score=min_score,
            temperature=0,
            max_tokens=1200,
        )

        result = self._parse_tool_result(
            tool_result
        )

        if not result.get("success", False):
            return {
                "success": False,
                "message": "RAG 问答失败。",
                "tool_result": result,
            }

        data = result.get("data", {})

        if not isinstance(data, dict):
            data = {}

        answer = data.get(
            "answer",
            "工具没有返回答案。",
        )

        self.stats[
            "questions_asked"
        ] += 1

        # 问答已经实际发生，
        # 因此把它记录为情景记忆。
        memory_content = (
            f"在会话 {self.session_id} 中，"
            f"用户询问“{question}”。"
            f"回答摘要：{str(answer)[:300]}"
        )

        self._record_memory(
            content=memory_content,
            memory_type="episodic",
            importance=0.7,
        )

        return {
            "success": True,
            "question": question,
            "answer": answer,
            "sources": data.get(
                "sources",
                [],
            ),
            "source_count": data.get(
                "source_count",
                0,
            ),
        }

    def add_note(
        self,
        content: str,
    ) -> dict[str, Any]:
        """
        将学习笔记保存为语义记忆。
        """

        if not isinstance(content, str):
            raise TypeError(
                "content 必须是字符串。"
            )

        content = content.strip()

        if not content:
            raise ValueError(
                "学习笔记不能为空。"
            )

        result = self._record_memory(
            content=content,
            memory_type="semantic",
            importance=0.8,
        )

        if result.get("success", False):
            self.stats[
                "notes_added"
            ] += 1

        return result

    def recall(
        self,
        query: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        从不同类型的记忆中回顾学习内容。
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

        result = self.memory_tool.execute(
            "search",
            query=query,
            memory_types=[
                "working",
                "episodic",
                "semantic",
            ],
            limit=limit,
        )

        return self._parse_tool_result(
            result
        )

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """
        获取当前学习助手的综合统计。
        """

        duration_seconds = (
            datetime.now()
            - self.session_start
        ).total_seconds()

        memory_stats = (
            self._parse_tool_result(
                self.memory_tool.execute(
                    "stats"
                )
            )
        )

        rag_stats = (
            self._parse_tool_result(
                self.rag_tool.execute(
                    "stats"
                )
            )
        )

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "session_start":
                self.session_start.isoformat(
                    timespec="seconds"
                ),
            "duration_seconds": round(
                duration_seconds,
                2,
            ),
            "documents_loaded":
                self.stats[
                    "documents_loaded"
                ],
            "questions_asked":
                self.stats[
                    "questions_asked"
                ],
            "notes_added":
                self.stats[
                    "notes_added"
                ],
            "current_documents":
                list(
                    self.current_documents
                ),
            "memory_stats": memory_stats,
            "rag_stats": rag_stats,
        }

    def generate_report(
        self,
        save_to_file: bool = True,
    ) -> dict[str, Any]:
        """
        生成当前会话的学习报告。
        """

        report = {
            "session": {
                "session_id":
                    self.session_id,
                "user_id":
                    self.user_id,
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
            },
            "stats": self.get_stats(),
            "recent_learning": self.recall(
                query="学习",
                limit=10,
            ),
        }

        if save_to_file:
            report_path = (
                self.report_dir
                / (
                    "learning_report_"
                    f"{self.session_id}.json"
                )
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

            report["report_file"] = str(
                report_path
            )

        return report