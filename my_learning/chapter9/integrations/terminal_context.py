import re
from datetime import datetime
from typing import Any

from context import ContextBuilder, ContextPacket
from tools import TerminalTool


class TerminalContextAdapter:
    """
    TerminalTool 与 ContextBuilder 之间的适配器。

    主要职责：

    1. 调用 TerminalTool 获取即时文件信息；
    2. 将工具输出包装成 ContextPacket；
    3. 将代码信息注入 ContextBuilder。
    """

    def __init__(
        self,
        terminal_tool: TerminalTool,
        context_builder: ContextBuilder,
    ) -> None:
        """
        初始化适配器。

        terminal_tool:
            用于安全访问代码库。

        context_builder:
            用于筛选、组织和压缩上下文。
        """

        self.terminal_tool = terminal_tool
        self.context_builder = context_builder

    def _create_packet(
        self,
        title: str,
        output: str,
        packet_type: str,
        relevance_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> ContextPacket:
        """
        将一次 TerminalTool 输出转换成 ContextPacket。
        """

        if not isinstance(title, str):
            raise TypeError(
                "title 必须是字符串。"
            )

        if not isinstance(output, str):
            raise TypeError(
                "output 必须是字符串。"
            )

        content = (
            f"[{title}]\n"
            f"{output}"
        )

        packet_metadata: dict[str, Any] = {
            "type": packet_type,
            "source": "terminal",
        }

        if metadata:
            packet_metadata.update(metadata)

        return ContextPacket(
            content=content,
            timestamp=datetime.now(),
            token_count=(
                self.context_builder
                ._count_tokens(content)
            ),
            relevance_score=relevance_score,
            metadata=packet_metadata,
        )

    def collect_structure(
        self,
        path: str = ".",
        max_depth: int = 2,
    ) -> ContextPacket:
        """
        获取指定目录的目录树。
        """

        output = self.terminal_tool.run({
            "action": "tree",
            "path": path,
            "max_depth": max_depth,
        })

        return self._create_packet(
            title="代码库结构",
            output=output,
            packet_type="code_structure",
            relevance_score=0.70,
            metadata={
                "path": path,
                "max_depth": max_depth,
            },
        )

    def collect_search(
        self,
        query: str,
        path: str = ".",
        max_results: int = 20,
        case_sensitive: bool = False,
    ) -> ContextPacket:
        """
        在代码库中搜索指定内容。
        """

        output = self.terminal_tool.run({
            "action": "search_text",
            "query": query,
            "path": path,
            "max_results": max_results,
            "case_sensitive": case_sensitive,
        })

        return self._create_packet(
            title=f"代码搜索结果：{query}",
            output=output,
            packet_type="code_search",
            relevance_score=0.85,
            metadata={
                "query": query,
                "path": path,
            },
        )

    def collect_file(
        self,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> ContextPacket:
        """
        读取指定文件的部分内容。
        """

        output = self.terminal_tool.run({
            "action": "read_file",
            "path": path,
            "start_line": start_line,
            "end_line": end_line,
        })

        return self._create_packet(
            title=f"文件内容：{path}",
            output=output,
            packet_type="code_file",
            relevance_score=0.90,
            metadata={
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
            },
        )

    def collect_file_info(
        self,
        path: str,
    ) -> ContextPacket:
        """
        获取文件或目录的基础信息。
        """

        output = self.terminal_tool.run({
            "action": "file_info",
            "path": path,
        })

        return self._create_packet(
            title=f"文件信息：{path}",
            output=output,
            packet_type="file_info",
            relevance_score=0.65,
            metadata={
                "path": path,
            },
        )

    def build_context(
        self,
        user_query: str,
        terminal_packets: list[ContextPacket],
        conversation_history: list[Any] | None = None,
        system_instructions: str | None = None,
        additional_packets: (
            list[ContextPacket] | None
        ) = None,
    ) -> str:
        """
        将 TerminalTool 结果注入 ContextBuilder。

        additional_packets 可以用于同时传入：

        - NoteTool 笔记；
        - Memory 检索结果；
        - 其他外部信息。
        """

        custom_packets = list(
            terminal_packets
        )

        if additional_packets:
            custom_packets.extend(
                additional_packets
            )

        return self.context_builder.build(
            user_query=user_query,
            conversation_history=(
                conversation_history
            ),
            system_instructions=(
                system_instructions
            ),
            custom_packets=custom_packets,
        )
    



    def collect_search_context(
        self,
        query: str,
        path: str = ".",
        max_results: int = 20,
        max_matches: int = 2,
        context_lines: int = 30,
    ) -> list[ContextPacket]:
        """
        先搜索代码，再自动读取命中位置附近的源码。

        返回内容包括：

        1. 一条代码搜索结果信息包；
        2. 若干条命中位置附近的源码信息包。

        例如搜索：

            class ContextBuilder

        得到：

            builder.py:8: class ContextBuilder:

        然后自动读取 builder.py 第 1～38 行附近的代码。
        """

        if max_results <= 0:
            raise ValueError(
                "max_results 必须大于 0。"
            )

        if max_matches <= 0:
            raise ValueError(
                "max_matches 必须大于 0。"
            )

        if context_lines <= 0:
            raise ValueError(
                "context_lines 必须大于 0。"
            )

        # 第一步：搜索代码。
        search_packet = self.collect_search(
            query=query,
            path=path,
            max_results=max_results,
        )

        packets = [search_packet]

        # TerminalTool 的搜索结果格式类似：
        #
        # my_learning/chapter9/context/builder.py:10:
        # class ContextBuilder:
        #
        # 提取文件路径和行号。
        matches = re.findall(
            r"(?m)^(.+?\.py):(\d+):",
            search_packet.content,
        )

        seen_ranges: set[
            tuple[str, int, int]
        ] = set()

        for file_path, line_text in matches:
            line_number = int(line_text)

            start_line = max(
                1,
                line_number - context_lines,
            )

            end_line = (
                line_number + context_lines
            )

            range_key = (
                file_path,
                start_line,
                end_line,
            )

            if range_key in seen_ranges:
                continue

            try:
                file_packet = self.collect_file(
                    path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                )
            except (
                FileNotFoundError,
                PermissionError,
                ValueError,
                OSError,
            ) as error:
                print(
                    "[WARNING] "
                    f"读取搜索结果对应文件失败："
                    f"{file_path}，{error}"
                )

                continue

            packets.append(file_packet)
            seen_ranges.add(range_key)

            if len(seen_ranges) >= max_matches:
                break

        return packets