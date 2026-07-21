import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT=Path(__file__).resolve().parents[2]
ENV_PATH=PROJECT_ROOT/".env"

load_dotenv(ENV_PATH)

api_key=os.getenv("DASHSCOPE_API_KEY")
base_url=os.getenv("LLM_BASE_URL")
model_id=os.getenv("LLM_MODEL_ID")

if not api_key:
    raise ValueError()

if not base_url:
    raise ValueError()

if not model_id:
    raise ValueError()

client=OpenAI(
    api_key=api_key,
    base_url=base_url,
)

def call_llm(user_prompt:str)->str:
    """
    调用大模型
    """
    
    try:
        response=client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role":"system",
                    "content":(
                        "你是一个智能体决策助手"
                        "请严格按照以下格式回答：\n"
                        "Thought: 你的思考\n"
                        "Action: 你的行动"
                    ),
                },
                {
                    "role":"user",
                    "content":user_prompt,
                },
            ],
            stream=False,
        )

        content=response.choices[0].message.content

        if not content:
            return "模型没有返回文本内容"
        
        return content
    
    except Exception as error:
        return f"模型调用失败：{type(error).__name__}:{error}"
    
if __name__=="__main__":
    prompt=(
        "用户想知道南京当前的天气。"
        "现在有一个名为 get_weather 的工具，参数是 city。"
        "请决定下一步行动。"
    )

    print("正在调用模型......")

    result=call_llm(prompt)

    print("\n模型返回：")
    print("-"*66)
    print(result)
    print("-"*66)