from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """
    Agent 框架的统一配置对象。

    temperature:
        控制模型输出随机性。
        数值越低，输出通常越稳定。

    max_tokens:
        限制模型单次最多生成的 token 数。
        为 None 时，由模型服务决定。

    max_history_length:
        Agent 最多保存多少条历史消息。

    max_steps:
        ReAct、Reflection 等 Agent 最多执行多少轮，
        用来防止无限循环。

    debug:
        是否开启调试模式。
    """

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    max_history_length: int = 100
    max_steps: int = 10
    debug: bool = False