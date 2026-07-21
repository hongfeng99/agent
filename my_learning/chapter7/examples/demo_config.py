from hello_agents.config import Config


def main() -> None:
    """
    测试 Config 配置对象。
    """

    default_config = Config()

    print("默认配置：")
    print(default_config)

    custom_config = Config(
        temperature=0,
        max_tokens=500,
        max_history_length=20,
        max_steps=5,
        debug=True,
    )

    print("\n自定义配置：")
    print(custom_config)

    print("\n自定义 temperature：")
    print(custom_config.temperature)

    print("\n自定义最大历史消息数量：")
    print(custom_config.max_history_length)

    print("\n是否开启调试模式：")
    print(custom_config.debug)


if __name__ == "__main__":
    main()