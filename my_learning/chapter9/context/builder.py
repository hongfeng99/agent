import math
import re
from datetime import datetime
from typing import Any

from .models import ContextConfig, ContextPacket

class ContextBuilder:
    """
    上下文构建器。

    负责按照 GSSC 流程构建上下文：

    1. Gather：收集候选信息；
    2. Select：筛选高价值信息；
    3. Structure：整理成固定结构；
    4. Compress：超出预算时进行压缩。

    当前版本先实现：

    - 初始化；
    - token 数量估算；
    - Gather 信息汇集。
    """

    def __init__(
        self,
        memory_tool: Any | None = None,
        rag_tool: Any | None = None,
        config: ContextConfig | None = None,
    ) -> None:
        """
        初始化上下文构建器。

        memory_tool:
            记忆检索工具。
            当前版本暂时只保存，不调用。

        rag_tool:
            RAG 检索工具。
            当前版本暂时只保存，不调用。

        config:
            上下文构建配置。
            如果没有传入，就使用默认的 ContextConfig。
        """

        self.memory_tool = memory_tool
        self.rag_tool = rag_tool

        if config is None:
            config = ContextConfig()

        self.config = config


    def _count_tokens(self, text: str) -> int:
        """
        粗略估算一段文本包含的 token 数量。

        当前采用简化规则：

        - 一个中文字符约等于一个 token；
        - 一个英文单词约等于 1.3 个 token。

        生产环境通常会使用模型对应的 tokenizer
        进行更加精确的计算。
        """

        if not isinstance(text, str):
            raise TypeError("text 必须是字符串。")

        if not text:
            return 0

        # 统计中文字符数量。
        chinese_chars = sum(
            1
            for char in text
            if "\u4e00" <= char <= "\u9fff"
        )

        # 统计由空格分隔的内容数量。
        english_words = len(
            [
                word
                for word in text.split()
                if word
            ]
        )

        estimated_tokens = int(
            chinese_chars
            + english_words * 1.3
        )

        # 非空文本至少按一个 token 计算。
        return max(1, estimated_tokens)
    


    def _get_message_value(
        self,
        message: Any,
        field_name: str,
        default: Any = None,
    ) -> Any:
        """
        从消息中读取指定字段。

        同时支持：

        1. 字典消息；
        2. Message 对象。
        """

        if isinstance(message, dict):
            return message.get(
                field_name,
                default,
            )

        return getattr(
            message,
            field_name,
            default,
        )
    


    def _gather(
        self,
        user_query: str,
        conversation_history: list[Any] | None = None,
        system_instructions: str | None = None,
        custom_packets: list[ContextPacket] | None = None,
    ) -> list[ContextPacket]:
        """
        汇集候选上下文信息。

        user_query:
            用户当前提出的问题。

            当前版本暂时不直接将它包装成 ContextPacket，
            后续会在 Structure 阶段放入 [Task] 分区。

        conversation_history:
            之前的对话历史。
            当前只读取最近 5 条。

        system_instructions:
            Agent 的角色和行为要求。

        custom_packets:
            调用者直接提供的自定义上下文信息包。

        返回：
            汇集到的 ContextPacket 列表。
        """

        if not isinstance(user_query, str):
            raise TypeError(
                "user_query 必须是字符串。"
            )

        if not user_query.strip():
            raise ValueError(
                "user_query 不能为空。"
            )

        packets: list[ContextPacket] = []

        # 1. 添加系统指令。
        if system_instructions:
            system_instructions = (
                system_instructions.strip()
            )

            if system_instructions:
                packets.append(
                    ContextPacket(
                        content=system_instructions,
                        timestamp=datetime.now(),
                        token_count=self._count_tokens(
                            system_instructions
                        ),
                        relevance_score=1.0,
                        metadata={
                            "type": "system_instruction",
                            "priority": "high",
                        },
                    )
                )

        # 2. 添加最近 5 条对话历史。
        if conversation_history:
            recent_history = (
                conversation_history[-5:]
            )

            for message in recent_history:
                role = self._get_message_value(
                    message,
                    "role",
                    "unknown",
                )

                content = self._get_message_value(
                    message,
                    "content",
                    "",
                )

                timestamp = self._get_message_value(
                    message,
                    "timestamp",
                    datetime.now(),
                )

                # 跳过没有正文的消息。
                if not isinstance(content, str):
                    continue

                content = content.strip()

                if not content:
                    continue

                # 如果时间戳无效，就使用当前时间。
                if not isinstance(
                    timestamp,
                    datetime,
                ):
                    timestamp = datetime.now()

                formatted_content = (
                    f"{role}: {content}"
                )

                packets.append(
                    ContextPacket(
                        content=formatted_content,
                        timestamp=timestamp,
                        token_count=self._count_tokens(
                            formatted_content
                        ),
                        relevance_score=0.6,
                        metadata={
                            "type": "conversation_history",
                            "role": role,
                        },
                    )
                )

        # 3. 添加调用者传入的自定义信息包。
        if custom_packets:
            for packet in custom_packets:
                if not isinstance(
                    packet,
                    ContextPacket,
                ):
                    raise TypeError(
                        "custom_packets 中的元素"
                        "必须是 ContextPacket。"
                    )

                packets.append(packet)

        print(
            f"[ContextBuilder] "
            f"汇集了 {len(packets)} 个候选信息包。"
        )

        return packets
    

    def _tokenize(self, text: str) -> set[str]:
        """
        将文本简单切分成词项集合。

        当前规则：

        1. 中文按照单个汉字切分；
        2. 英文和数字按照连续字符串切分；
        3. 统一转换成小写；
        4. 使用集合去除重复词项。

        例如：

        "学习 Chapter 9"

        会转换成：

        {"学", "习", "chapter", "9"}
        """

        if not isinstance(text, str):
            raise TypeError("text 必须是字符串。")

        normalized_text = text.lower()

        tokens = re.findall(
            r"[\u4e00-\u9fff]|[a-z0-9_]+",
            normalized_text,
        )

        return set(tokens)
    


    def _calculate_relevance(
        self,
        content: str,
        query: str,
    ) -> float:
        """
        计算信息内容与用户问题之间的相关性。

        当前使用 Jaccard 相似度：

        相关性 =
        共同词项数量 / 全部不同词项数量

        返回值范围为 0.0～1.0。
        """

        content_words = self._tokenize(content)
        query_words = self._tokenize(query)

        if not query_words:
            return 0.0

        intersection = (
            content_words & query_words
        )

        union = (
            content_words | query_words
        )

        if not union:
            return 0.0

        relevance_score = (
            len(intersection) / len(union)
        )

        return relevance_score
    


    def _calculate_recency(
        self,
        timestamp: datetime,
    ) -> float:
        """
        根据信息产生时间计算新近性分数。

        越新的信息分数越接近 1.0；
        越旧的信息分数越低。

        最低分数限制为 0.1。
        """

        if not isinstance(timestamp, datetime):
            raise TypeError(
                "timestamp 必须是 datetime 对象。"
            )

        age_hours = (
            datetime.now() - timestamp
        ).total_seconds() / 3600

        # 防止未来时间产生负数。
        age_hours = max(
            0.0,
            age_hours,
        )

        decay_factor = 0.1

        recency_score = math.exp(
            -decay_factor
            * age_hours
            / 24
        )

        return max(
            0.1,
            min(1.0, recency_score),
        )



    def _select(
        self,
        packets: list[ContextPacket],
        user_query: str,
        available_tokens: int,
    ) -> list[ContextPacket]:
        """
        根据相关性、新近性和 token 预算选择信息包。

        处理流程：

        1. 单独取出系统指令；
        2. 为其他信息计算相关性；
        3. 计算新近性；
        4. 计算综合分数；
        5. 过滤低相关信息；
        6. 按综合分数降序排列；
        7. 在 token 预算内依次选择。
        """

        if not isinstance(user_query, str):
            raise TypeError(
                "user_query 必须是字符串。"
            )

        if not user_query.strip():
            raise ValueError(
                "user_query 不能为空。"
            )

        if available_tokens <= 0:
            raise ValueError(
                "available_tokens 必须大于 0。"
            )

        # 1. 分离系统指令和普通信息。
        system_packets = [
            packet
            for packet in packets
            if (packet.metadata or {}).get("type")
            == "system_instruction"
        ]

        other_packets = [
            packet
            for packet in packets
            if (packet.metadata or {}).get("type")
            != "system_instruction"
        ]

        # 2. 统计系统指令使用的 token。
        system_tokens = sum(
            packet.token_count
            for packet in system_packets
        )

        # 即使系统指令超出预算，也优先保留。
        if system_tokens >= available_tokens:
            print(
                "[WARNING] "
                "系统指令已经占满 token 预算。"
            )

            return system_packets

        # 保存：
        # (综合分数, 信息包)
        scored_packets: list[
            tuple[float, ContextPacket]
        ] = []

        # 3. 为普通信息计算分数。
        for packet in other_packets:
            # 0.5 是 ContextPacket 的默认分数，
            # 表示尚未针对当前问题计算相关性。
            if packet.relevance_score == 0.5:
                packet.relevance_score = (
                    self._calculate_relevance(
                        content=packet.content,
                        query=user_query,
                    )
                )

            # 4. 过滤低相关信息。
            if (
                packet.relevance_score
                < self.config.min_relevance
            ):
                continue

            # 5. 计算新近性。
            recency_score = (
                self._calculate_recency(
                    packet.timestamp
                )
            )

            # 6. 计算综合分数。
            combined_score = (
                self.config.relevance_weight
                * packet.relevance_score
                + self.config.recency_weight
                * recency_score
            )

            # 把评分写入元数据，方便观察结果。
            if packet.metadata is None:
                packet.metadata = {}

            packet.metadata["recency_score"] = round(
                recency_score,
                4,
            )

            packet.metadata["combined_score"] = round(
                combined_score,
                4,
            )

            scored_packets.append(
                (
                    combined_score,
                    packet,
                )
            )

        # 7. 按照综合分数从高到低排序。
        scored_packets.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        # 8. 系统指令首先进入最终结果。
        selected_packets = system_packets.copy()

        current_tokens = system_tokens

        # 9. 按照分数顺序填充 token 预算。
        for score, packet in scored_packets:
            new_token_total = (
                current_tokens
                + packet.token_count
            )

            if new_token_total <= available_tokens:
                selected_packets.append(packet)
                current_tokens = new_token_total
            else:
                # 当前预算已经不能再容纳该信息。
                break

        print(
            "[ContextBuilder] "
            f"选择了 {len(selected_packets)} 个信息包，"
            f"共 {current_tokens} tokens。"
        )

        return selected_packets
    


    def _structure(
        self,
        selected_packets: list[ContextPacket],
        user_query: str,
    ) -> str:
        """
        将选中的信息包组织成结构化上下文。

        分区说明：

        [Role & Policies]
            Agent 的角色和行为要求。

        [Task]
            用户当前提出的问题。

        [Evidence]
            RAG、知识库等外部证据。

        [Context]
            对话历史、记忆和其他补充信息。

        [Output]
            对模型输出结果的要求。
        """

        if not isinstance(user_query, str):
            raise TypeError(
                "user_query 必须是字符串。"
            )

        user_query = user_query.strip()

        if not user_query:
            raise ValueError(
                "user_query 不能为空。"
            )

        if not isinstance(
            selected_packets,
            list,
        ):
            raise TypeError(
                "selected_packets 必须是列表。"
            )

        # 分别保存不同类型的上下文。
        system_instructions: list[str] = []
        evidence: list[str] = []
        context: list[str] = []

        # 1. 按照信息类型进行分组。
        for packet in selected_packets:
            if not isinstance(
                packet,
                ContextPacket,
            ):
                raise TypeError(
                    "selected_packets 中的元素"
                    "必须是 ContextPacket。"
                )

            metadata = packet.metadata or {}

            packet_type = metadata.get(
                "type",
                "general",
            )

            packet_source = metadata.get(
                "source",
                "",
            )

            if packet_type == "system_instruction":
                system_instructions.append(
                    packet.content
                )

            elif (
                packet_type
                in {
                    "rag_result",
                    "knowledge",
                    "code_structure",
                    "code_search",
                    "code_file",
                    "file_info",
                }
                or packet_source == "terminal"
            ):
                evidence.append(
                    packet.content
                )

            else:
                context.append(
                    packet.content
                )

        # 2. 按照固定结构构造上下文。
        sections: list[str] = []

        if system_instructions:
            sections.append(
                "[Role & Policies]\n"
                + "\n".join(
                    system_instructions
                )
            )

        # 当前用户任务必须存在。
        sections.append(
            "[Task]\n"
            + user_query
        )

        if evidence:
            sections.append(
                "[Evidence]\n"
                + "\n---\n".join(
                    evidence
                )
            )

        if context:
            sections.append(
                "[Context]\n"
                + "\n".join(
                    context
                )
            )

        sections.append(
            "[Output]\n"
            "请基于以上信息，提供准确、清晰且有依据的回答。"
        )

        # 不同分区之间空一行。
        structured_context = (
            "\n\n".join(sections)
        )

        print(
            "[ContextBuilder] "
            f"完成上下文结构化，"
            f"共 {self._count_tokens(structured_context)} tokens。"
        )

        return structured_context
    


    def _truncate_text(
        self,
        text: str,
        max_tokens: int,
    ) -> str:
        """
        将文本截断到指定的 token 数量以内。

        当前使用字符数量与 token 数量之间的比例，
        粗略计算应该保留多少字符。

        生产环境可以改用模型对应的 tokenizer。
        """

        if not isinstance(text, str):
            raise TypeError(
                "text 必须是字符串。"
            )

        if max_tokens <= 0:
            return ""

        current_tokens = self._count_tokens(text)

        # 原文本本身没有超过限制，不需要截断。
        if current_tokens <= max_tokens:
            return text

        if current_tokens == 0:
            return ""

        # 估算平均每个 token 对应多少字符。
        chars_per_token = (
            len(text) / current_tokens
        )

        # 根据 token 上限估算最多保留多少字符。
        max_chars = int(
            max_tokens * chars_per_token
        )

        max_chars = max(
            1,
            max_chars,
        )

        truncated_text = text[:max_chars]

        # 由于上面的计算只是估算，
        # 再检查一次，确保结果没有超过 token 上限。
        while (
            truncated_text
            and self._count_tokens(truncated_text)
            > max_tokens
        ):
            truncated_text = truncated_text[:-1]

        return truncated_text
    


    def _compress(
        self,
        context: str,
        max_tokens: int,
    ) -> str:
        """
        对超过 token 限制的上下文进行压缩。

        当前采用分区压缩策略：

        1. 没有超过限制时，直接返回原上下文；
        2. 按照空行切分上下文分区；
        3. 能够完整放入的分区全部保留；
        4. 当前分区无法完整放入时，对其进行截断；
        5. 截断后停止继续添加后续内容。
        """

        if not isinstance(context, str):
            raise TypeError(
                "context 必须是字符串。"
            )

        if max_tokens <= 0:
            raise ValueError(
                "max_tokens 必须大于 0。"
            )

        current_tokens = self._count_tokens(
            context
        )

        # 没有超过限制，不需要压缩。
        if current_tokens <= max_tokens:
            print(
                "[ContextBuilder] "
                "上下文未超限，无需压缩。"
            )

            return context

        print(
            "[ContextBuilder] "
            f"上下文超限："
            f"{current_tokens} > {max_tokens}，"
            "开始执行压缩。"
        )

        # _structure() 使用两个换行符分隔各个分区。
        sections = context.split("\n\n")

        compressed_sections: list[str] = []

        current_total = 0

        compression_marker = (
            "\n[... 内容已压缩 ...]"
        )

        marker_tokens = self._count_tokens(
            compression_marker
        )

        for section in sections:
            section_tokens = self._count_tokens(
                section
            )

            new_total = (
                current_total
                + section_tokens
            )

            # 当前分区可以完整放入。
            if new_total <= max_tokens:
                compressed_sections.append(
                    section
                )

                current_total = new_total

                continue

            # 当前分区无法完整放入。
            remaining_tokens = (
                max_tokens
                - current_total
            )

            # 至少剩余一定空间时，
            # 才对当前分区进行部分保留。
            if remaining_tokens > 50:
                content_tokens = max(
                    1,
                    remaining_tokens
                    - marker_tokens,
                )

                truncated_section = (
                    self._truncate_text(
                        text=section,
                        max_tokens=content_tokens,
                    )
                )

                compressed_sections.append(
                    truncated_section
                    + compression_marker
                )

            # 一旦预算不足，就结束压缩。
            break

        compressed_context = "\n\n".join(
            compressed_sections
        )

        final_tokens = self._count_tokens(
            compressed_context
        )

        print(
            "[ContextBuilder] "
            f"压缩完成："
            f"{current_tokens} -> {final_tokens} tokens。"
        )

        return compressed_context
    



    def build(
        self,
        user_query: str,
        conversation_history: list[Any] | None = None,
        system_instructions: str | None = None,
        custom_packets: list[ContextPacket] | None = None,
    ) -> str:
        """
        构建最终上下文。

        完整执行 GSSC 流水线：

        1. Gather：汇集候选信息；
        2. Select：筛选高价值信息；
        3. Structure：构造固定上下文结构；
        4. Compress：对超限上下文进行压缩。
        """

        if not isinstance(user_query, str):
            raise TypeError(
                "user_query 必须是字符串。"
            )

        user_query = user_query.strip()

        if not user_query:
            raise ValueError(
                "user_query 不能为空。"
            )

        print(
            "\n[ContextBuilder] "
            "开始构建上下文。"
        )

        # 1. Gather：收集候选信息。
        packets = self._gather(
            user_query=user_query,
            conversation_history=conversation_history,
            system_instructions=system_instructions,
            custom_packets=custom_packets,
        )

        # 给 Task、Output 和结构标题预留一部分空间。
        available_tokens = int(
            self.config.max_tokens
            * (
                1.0
                - self.config.reserve_ratio
            )
        )

        available_tokens = max(
            1,
            available_tokens,
        )

        print(
            "[ContextBuilder] "
            f"信息包可用预算："
            f"{available_tokens} tokens。"
        )

        # 2. Select：筛选候选信息。
        selected_packets = self._select(
            packets=packets,
            user_query=user_query,
            available_tokens=available_tokens,
        )

        # 3. Structure：整理成固定结构。
        structured_context = self._structure(
            selected_packets=selected_packets,
            user_query=user_query,
        )

        # 4. Compress：根据配置决定是否压缩。
        if self.config.enable_compression:
            final_context = self._compress(
                context=structured_context,
                max_tokens=self.config.max_tokens,
            )
        else:
            final_context = structured_context

            final_tokens = self._count_tokens(
                final_context
            )

            if final_tokens > self.config.max_tokens:
                print(
                    "[WARNING] "
                    "上下文已经超过 max_tokens，"
                    "但 enable_compression=False，"
                    "因此没有执行压缩。"
                )

        print(
            "[ContextBuilder] "
            "上下文构建完成。"
        )

        return final_context