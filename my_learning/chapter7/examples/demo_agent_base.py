from hello_agents.agent import Agent
from hello_agents.config import Config
from hello_agents.llm import HelloAgentsLLM
from hello_agents.message import Message


class DemoAgent(Agent):
    """
    用于测试 Agent 基类的临时 Agent。

    目前不调用大模型，只测试：
    1. run() 方法重写；
    2. 历史记录保存；
    3. 历史记录长度限制；
    4. 消息列表构造。
    """

    def run(self, input_text: str, **kwargs) -> str:
        response = f"{self.name} 收到用户输入：{input_text}"

        self.add_message(
            Message(
                role="user",
                content=input_text,
            )
        )

        self.add_message(
            Message(
                role="assistant",
                content=response,
            )
        )

        return response


def main() -> None:
    llm = HelloAgentsLLM()

    config = Config(
        max_history_length=4,
        debug=True,
    )

    agent = DemoAgent(
        name="DemoAgent",
        llm=llm,
        system_prompt="你是一个测试 Agent。",
        config=config,
    )

    result1 = agent.run("第一条消息")
    print("第一次运行结果：")
    print(result1)

    result2 = agent.run("第二条消息")
    print("\n第二次运行结果：")
    print(result2)

    print("\n当前历史消息：")

    for message in agent.get_history():
        print(message)

    print("\n发送给模型的消息格式：")

    messages = agent._build_messages(
        current_input="第三条消息",
    )

    for message in messages:
        print(message)

    agent.clear_history()

    print("\n清空后的历史消息：")
    print(agent.get_history())


if __name__ == "__main__":
    main()