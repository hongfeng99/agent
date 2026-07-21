import sys
from pathlib import Path


# chapter8 根目录
CHAPTER8_DIR = (
    Path(__file__).resolve().parents[1]
)

# chapter7 根目录
CHAPTER7_DIR = (
    CHAPTER8_DIR.parent / "chapter7"
)


# 让测试代码能够导入 chapter8 中的：
#
# memory
# tools
# assistant
if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(CHAPTER8_DIR),
    )


# 后续测试 RAGTool、AgentMemoryTool 时，
# 需要导入 chapter7 中的 hello_agents。
if str(CHAPTER7_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(CHAPTER7_DIR),
    )