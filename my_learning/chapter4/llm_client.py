import os
from typing import Dict,List,Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class HelloAgentsLLM:
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        
        self.model=model or os.getenv("LLM_MODEL_ID")
        api_key=api_key or os.getenv("LLM_API_KEY")
        base_url=base_url or os.getenv("LLM_BASE_URL")
        timeout=timeout or int(os.getenv("LLM_TIMEOUT","66"))

        if not self.model:
            raise ValueError("没有配置 LLM_MODEL_ID")

        if not api_key:
            raise ValueError("没有配置 LLM_API_KEY")

        if not base_url:
            raise ValueError("没有配置 LLM_BASE_URL")
        
        self.client=OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def think(
            self,
            messages:List[Dict[str,str]],
            temperature:float=0,
    )->Optional[str]:
        
        print(f"\n正在调用模型：{self.model}")

        try:
            response=self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )

            collected_content=[]

            for chunk in response:
                if not chunk.choices:
                    continue

                content=chunk.choices[0].delta.content or ""

                # 一边接收，一边显示模型输出
                print(content, end="", flush=True)

                collected_content.append(content)

            print()

            # 把流式返回的多个文本片段拼接起来
            return "".join(collected_content)

        except Exception as error:
            print(f"\n调用模型失败：{error}")
            return None
        
def main():

    try:
        llm_client=HelloAgentsLLM()

        messages=[
            {
                "role":"system",
                "content":"你是一名耐心的 Python 和智能体开发老师",
            },
            {
                "role":"user",
                "content":(
                    "请用三句话解释 ReAct 智能体中的 "
                    "Thought、Action 和 Observation。"
                ),
            },
        ]

        answer=llm_client.think(messages)

        if answer:
            print("\n--- 最终获得的完整结果 ---")
            print(answer)
        else:
            print("模型没有返回有效结果。")

    except ValueError as error:
        print(f"配置错误：{error}")

if __name__=="__main__":
    main()