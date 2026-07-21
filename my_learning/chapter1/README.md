# Hello-Agents Chapter 1 学习记录

## 1. 学习目标

- 理解智能体的基本定义
- 理解 PEAS 模型
- 理解 Agent Loop
- 理解 Thought-Action-Observation
- 理解 Workflow 和 Agent 的区别
- 从零实现一个智能旅行助手

## 2. 项目文件

| 文件 | 作用 |
|---|---|
| notes.md | Chapter 1 理论笔记 |
| exercises.md | Chapter 1 习题 |
| 01_weather_test.py | 单独测试天气工具 |
| 02_llm_test.py | 单独测试大模型 |
| 03_tavily_test.py | 单独测试搜索工具 |
| 04_first_agent.py | 完整智能旅行助手 |
| 05_agent_debug.py | Agent运行轨迹调试 |

## 3. Agent运行流程

用户提出任务
→ 大模型生成Thought和Action
→ Python解析Action
→ 从工具注册表查找函数
→ Python执行工具
→ 工具结果转换为Observation
→ Observation加入prompt_history
→ 大模型继续决策
→ Finish结束任务

## 4. 模型和Python的职责

### 大语言模型负责

- 理解用户目标
- 分析当前Observation
- 选择下一步工具
- 生成工具参数
- 判断何时结束

### Python程序负责

- 调用大语言模型
- 解析模型输出
- 查找并执行工具
- 捕获工具异常
- 保存执行历史
- 限制最大循环次数

## 5. 运行方式

```bash
conda activate hello-agents
python my_learning/chapter1/04_first_agent.py