import json
from typing import Any, Dict

from hello_agents.tools.base import Tool

from memory.rag import (
    RAGAnswer,
    RAGPipeline,
    RetrievalResult,
)


class RAGTool(Tool):
    """
    RAG 工具。

    将 RAGPipeline 封装成 Chapter 7 工具系统
    可以注册和调用的标准 Tool。

    支持的操作：

    1. add_file：添加文件；
    2. add_text：添加文本；
    3. search：检索相关文本块；
    4. ask：基于知识库生成答案；
    5. stats：查看知识库统计；
    6. clear：清空知识库。
    """

    SUPPORTED_ACTIONS = {
        "add_file",
        "add_text",
        "search",
        "ask",
        "stats",
        "clear",
    }

    def __init__(
        self,
        pipeline: RAGPipeline,
    ) -> None:
        """
        pipeline:
            已经配置好的 RAGPipeline。

            pipeline 中可以包含：

            - DocumentProcessor；
            - TF-IDF 嵌入模型；
            - HelloAgentsLLM。
        """

        if not isinstance(pipeline, RAGPipeline):
            raise TypeError(
                "pipeline 必须是 RAGPipeline 对象。"
            )

        super().__init__(
            name="rag",
            description="""
RAG 知识库工具。

当需要添加资料、搜索资料或根据资料回答问题时，
必须使用该工具。

支持以下 action：

1. add_file：添加 txt 或 md 文件
参数：
{
    "action": "add_file",
    "file_path": "文件路径"
}

2. add_text：添加一段文本
参数：
{
    "action": "add_text",
    "text": "文本内容",
    "metadata": {
        "source": "来源名称"
    }
}

3. search：检索相关文本块
参数：
{
    "action": "search",
    "query": "查询内容",
    "top_k": 3,
    "min_score": 0.01
}

4. ask：根据知识库回答问题
参数：
{
    "action": "ask",
    "question": "用户问题",
    "top_k": 3,
    "min_score": 0.01
}

5. stats：查看知识库统计
参数：
{
    "action": "stats"
}

6. clear：清空知识库
参数：
{
    "action": "clear"
}
""".strip(),
        )

        self.pipeline = pipeline

    def run(
        self,
        parameters: Dict[str, Any],
    ) -> str:
        """
        Chapter 7 工具系统调用的标准入口。

        无论操作成功还是失败，都返回 JSON 字符串，
        方便 Agent 继续读取工具执行结果。
        """

        try:
            if not isinstance(parameters, dict):
                raise TypeError(
                    "parameters 必须是字典。"
                )

            action = parameters.get("action")

            if not isinstance(action, str):
                raise ValueError(
                    "缺少字符串类型的 action 参数。"
                )

            action = action.strip()

            if not action:
                raise ValueError(
                    "action 不能为空。"
                )

            if action not in self.SUPPORTED_ACTIONS:
                raise ValueError(
                    f"不支持的 action：{action}。"
                    f"支持的操作："
                    f"{sorted(self.SUPPORTED_ACTIONS)}"
                )

            data = self._execute_action(
                action=action,
                parameters=parameters,
            )

            return self._to_json(
                {
                    "success": True,
                    "action": action,
                    "data": data,
                }
            )

        except Exception as error:
            return self._to_json(
                {
                    "success": False,
                    "action": (
                        parameters.get("action")
                        if isinstance(parameters, dict)
                        else None
                    ),
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )

    def execute(
        self,
        action: str,
        **kwargs: Any,
    ) -> str:
        """
        方便在普通 Python 代码中手动调用。

        例如：

        rag_tool.execute(
            "search",
            query="什么是工作记忆？",
            top_k=3,
        )

        execute 最终仍然会调用标准 run()。
        """

        parameters = {
            "action": action,
            **kwargs,
        }

        return self.run(parameters)

    def _execute_action(
        self,
        action: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        将不同 action 分发给对应的方法。
        """

        if action == "add_file":
            return self._add_file(parameters)

        if action == "add_text":
            return self._add_text(parameters)

        if action == "search":
            return self._search(parameters)

        if action == "ask":
            return self._ask(parameters)

        if action == "stats":
            return self.pipeline.stats()

        if action == "clear":
            cleared_count = self.pipeline.clear()

            return {
                "cleared_count": cleared_count,
                "document_count":
                    self.pipeline.document_count,
            }

        # 正常情况下不会进入这里，
        # 因为 run() 已经验证过 action。
        raise ValueError(
            f"无法处理 action：{action}"
        )

    def _add_file(
        self,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        添加 txt 或 md 文件。
        """

        file_path = parameters.get("file_path")

        if not isinstance(file_path, str):
            raise ValueError(
                "add_file 操作需要字符串类型的 "
                "file_path 参数。"
            )

        file_path = file_path.strip()

        if not file_path:
            raise ValueError(
                "file_path 不能为空。"
            )

        chunks = self.pipeline.add_file(
            file_path
        )

        return {
            "file_path": file_path,
            "added_chunk_count": len(chunks),
            "document_count":
                self.pipeline.document_count,
            "chunk_ids": [
                chunk.document_id
                for chunk in chunks
            ],
        }

    def _add_text(
        self,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        添加一段文本。
        """

        text = parameters.get("text")

        if not isinstance(text, str):
            raise ValueError(
                "add_text 操作需要字符串类型的 "
                "text 参数。"
            )

        text = text.strip()

        if not text:
            raise ValueError(
                "text 不能为空。"
            )

        metadata = parameters.get(
            "metadata"
        )

        if metadata is not None and not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata 必须是字典或 None。"
            )

        chunks = self.pipeline.add_text(
            text=text,
            metadata=metadata,
        )

        return {
            "added_chunk_count": len(chunks),
            "document_count":
                self.pipeline.document_count,
            "chunk_ids": [
                chunk.document_id
                for chunk in chunks
            ],
        }

    def _search(
        self,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        搜索与 query 相关的文本块。
        """

        query = parameters.get("query")

        if not isinstance(query, str):
            raise ValueError(
                "search 操作需要字符串类型的 "
                "query 参数。"
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "query 不能为空。"
            )

        top_k = self._get_top_k(
            parameters
        )

        min_score = self._get_min_score(
            parameters
        )

        results = self.pipeline.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
        )

        return {
            "query": query,
            "result_count": len(results),
            "results": [
                self._retrieval_result_to_dict(
                    result
                )
                for result in results
            ],
        }

    def _ask(
        self,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        根据知识库回答 question。
        """

        question = parameters.get(
            "question"
        )

        # 为了提高工具容错能力，
        # ask 也允许模型使用 query 参数。
        if question is None:
            question = parameters.get("query")

        if not isinstance(question, str):
            raise ValueError(
                "ask 操作需要字符串类型的 "
                "question 参数。"
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "question 不能为空。"
            )

        top_k = self._get_top_k(
            parameters
        )

        min_score = self._get_min_score(
            parameters
        )

        temperature = parameters.get(
            "temperature",
            0,
        )

        max_tokens = parameters.get(
            "max_tokens",
            1000,
        )

        if not isinstance(
            temperature,
            (int, float),
        ):
            raise TypeError(
                "temperature 必须是数值。"
            )

        if not isinstance(max_tokens, int):
            raise TypeError(
                "max_tokens 必须是整数。"
            )

        if max_tokens <= 0:
            raise ValueError(
                "max_tokens 必须大于 0。"
            )

        rag_answer = self.pipeline.ask(
            question=question,
            top_k=top_k,
            min_score=min_score,
            temperature=float(
                temperature
            ),
            max_tokens=max_tokens,
        )

        return self._rag_answer_to_dict(
            rag_answer
        )

    @staticmethod
    def _get_top_k(
        parameters: Dict[str, Any],
    ) -> int:
        """
        获取 top_k。

        同时支持：

        - top_k；
        - limit。

        这样即使模型使用 limit，也可以正常工作。
        """

        top_k = parameters.get(
            "top_k",
            parameters.get("limit", 3),
        )

        if not isinstance(top_k, int):
            raise TypeError(
                "top_k 必须是整数。"
            )

        if top_k <= 0:
            raise ValueError(
                "top_k 必须大于 0。"
            )

        return top_k

    @staticmethod
    def _get_min_score(
        parameters: Dict[str, Any],
    ) -> float:
        """
        获取最低相似度。
        """

        min_score = parameters.get(
            "min_score",
            0.01,
        )

        if not isinstance(
            min_score,
            (int, float),
        ):
            raise TypeError(
                "min_score 必须是数值。"
            )

        if min_score < 0:
            raise ValueError(
                "min_score 不能小于 0。"
            )

        return float(min_score)

    @staticmethod
    def _retrieval_result_to_dict(
        result: RetrievalResult,
    ) -> Dict[str, Any]:
        """
        将 RetrievalResult 转换成
        可以被 json.dumps 处理的字典。
        """

        document = result.document

        return {
            "rank": result.rank,
            "score": round(
                result.score,
                6,
            ),
            "document_id":
                document.document_id,
            "content": document.content,
            "metadata": document.metadata,
        }

    def _rag_answer_to_dict(
        self,
        result: RAGAnswer,
    ) -> Dict[str, Any]:
        """
        将 RAGAnswer 转换成普通字典。
        """

        return {
            "question": result.question,
            "answer": result.answer,
            "source_count": len(
                result.retrieval_results
            ),
            "sources": [
                self._retrieval_result_to_dict(
                    retrieval_result
                )
                for retrieval_result
                in result.retrieval_results
            ],
        }

    @staticmethod
    def _to_json(
        data: Dict[str, Any],
    ) -> str:
        """
        将结果转换为格式化 JSON 字符串。
        """

        return json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        )