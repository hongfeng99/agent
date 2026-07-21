import sys
from pathlib import Path


# 当前 chapter8 目录
CHAPTER8_DIR = Path(__file__).resolve().parents[1]

# chapter7 目录
CHAPTER7_DIR = CHAPTER8_DIR.parent / "chapter7"

# 让 Python 能找到 chapter8 中的 memory 和 tools
if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER8_DIR))

# 让 Python 能找到 chapter7 中的 hello_agents
if str(CHAPTER7_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER7_DIR))


from hello_agents import (
    Config,
    HelloAgentsLLM,
    ReActAgent,
    ToolRegistry,
)

from memory.manager import MemoryManager
from memory.types.episodic import EpisodicMemory
from memory.types.working import WorkingMemory

from tools.agent_memory_tool import AgentMemoryTool
from tools.memory_tool import MemoryTool


DATA_DIR = CHAPTER8_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

EPISODIC_PATH = (
    DATA_DIR / "memory_agent_episodic.json"
)


def create_memory_tool() -> MemoryTool:
    """
    创建 Chapter 8 原有的 MemoryTool。
    """

    working_memory = WorkingMemory()

    episodic_memory = EpisodicMemory(
        storage_path=str(EPISODIC_PATH),
    )

    manager = MemoryManager(
        memories={
            "working": working_memory,
            "episodic": episodic_memory,
        }
    )

    return MemoryTool(manager)


def main() -> None:
    # 1. 创建原始记忆工具
    memory_tool = create_memory_tool()

    # 2. 转换成 Chapter 7 可以注册的工具
    agent_memory_tool = AgentMemoryTool(
        memory_tool=memory_tool,
    )

    # 3. 注册工具
    registry = ToolRegistry()
    registry.register(agent_memory_tool)

    # 4. 创建大模型
    llm = HelloAgentsLLM()

    config = Config(
        temperature=0,
        max_tokens=1000,
        max_history_length=20,
        max_steps=6,
        debug=True,
    )

    # 5. 创建具有记忆工具的 ReActAgent
    agent = ReActAgent(
        name="记忆助手",
        llm=llm,
        tool_registry=registry,
        system_prompt=(
            "你是一个具有长期记忆能力的助手。"
            "当用户要求记住、保存、查找或回顾信息时，"
            "必须调用 memory 工具。"
            "不能假装已经保存记忆。"
        ),
        config=config,
    )

    print("=" * 70)
    print("第一次任务：保存学习进度")
    print("=" * 70)

    add_result = agent.run(
        "请调用 memory 工具，"
        "把“我已经完成 Chapter 8 的基础记忆系统”"
        "保存为 episodic 记忆，"
        "importance 设置为 0.9。"
    )

    print("\n第一次回答：")
    print(add_result)

    print("\n" + "=" * 70)
    print("第二次任务：检索学习进度")
    print("=" * 70)

    search_result = agent.run(
        "请调用 memory 工具搜索与"
        "“Chapter 8 学习进度”有关的记忆，"
        "然后告诉我目前已经完成了什么。"
    )

    print("\n第二次回答：")
    print(search_result)

    print("\n" + "=" * 70)
    print("完整执行轨迹")
    print("=" * 70)

    for item in agent.current_trace:
        print(item)


if __name__ == "__main__":
    main()