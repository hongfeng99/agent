from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class ContextPacket:
    """
    候选上下文信息包。

    ContextBuilder 会从记忆、RAG、对话历史、系统指令等来源
    收集信息，并把每条信息统一封装成 ContextPacket。

    Attributes:
        content:
            信息的具体内容。

        timestamp:
            信息产生的时间，用于计算新近性分数。

        token_count:
            这段信息占用的 token 数量。

        relevance_score:
            信息与当前用户问题的相关性，取值范围为 0.0～1.0。

        metadata:
            信息的附加说明，例如信息类型、来源和角色。
    """

    content: str
    timestamp: datetime
    token_count: int
    relevance_score: float = 0.5
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        """
        ContextPacket 创建完成后，自动检查和修正数据。
        """

        # 如果没有传入 metadata，就创建一个空字典。
        if self.metadata is None:
            self.metadata = {}

        # 将相关性分数限制在 0.0～1.0。
        self.relevance_score = max(
            0.0,
            min(1.0, self.relevance_score),
        )


@dataclass
class ContextConfig:
    """
    上下文构建配置。

    Attributes:
        max_tokens:
            最终上下文允许使用的最大 token 数量。

        reserve_ratio:
            为系统指令等重要信息预留的比例。

        min_relevance:
            最低相关性阈值。低于该值的信息会被过滤。

        enable_compression:
            上下文超出限制时是否启用压缩。

        recency_weight:
            新近性分数在综合评分中的权重。

        relevance_weight:
            相关性分数在综合评分中的权重。
    """

    max_tokens: int = 3000
    reserve_ratio: float = 0.2
    min_relevance: float = 0.1
    enable_compression: bool = True
    recency_weight: float = 0.3
    relevance_weight: float = 0.7

    def __post_init__(self) -> None:
        """
        配置创建完成后，检查参数是否合法。
        """

        if self.max_tokens <= 0:
            raise ValueError("max_tokens 必须大于 0")

        if not 0.0 <= self.reserve_ratio <= 1.0:
            raise ValueError(
                "reserve_ratio 必须在 0.0～1.0 范围内"
            )

        if not 0.0 <= self.min_relevance <= 1.0:
            raise ValueError(
                "min_relevance 必须在 0.0～1.0 范围内"
            )

        weight_sum = (
            self.recency_weight
            + self.relevance_weight
        )

        if abs(weight_sum - 1.0) >= 1e-6:
            raise ValueError(
                "recency_weight 和 relevance_weight 的和必须等于 1.0"
            )