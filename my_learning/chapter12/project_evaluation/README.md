# 最小 Agent 评估系统

## 评估目标

本项目用于评估 Chapter 10 中实现的真实代码分析 Agent。

完整调用链路：

用户请求
→ A2A Server
→ MCP Server
→ 读取 Chapter 9 真实源码
→ LLM 分析
→ 返回结构化结果
→ 规则评估

## 评估指标

当前使用确定性规则检查：

1. 返回状态是否为 completed；
2. 回答是否包含 Gather、Select、Structure、Compress；
3. 是否读取 ContextBuilder 的五个关键方法；
4. 数据来源是否包含 MCP 和 ContextBuilder；
5. 是否出现“需要继续读取”等未完成内容；
6. 响应时间是否低于阈值；
7. 请求和 JSON 解析是否成功。

## 测试文件

- `test_cases.json`：测试用例与验收规则；
- `evaluate_code_agent.py`：评估执行器；
- `results/baseline.json`：完整基线报告；
- `results/baseline.csv`：简化基线报告。

## 运行方式

先启动远程代码分析服务：

```powershell
python -u my_learning/chapter10/examples/11_a2a_mcp_code_analyst_server.py