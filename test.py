from openai import OpenAI
from dotenv import load_dotenv
import os
# 加载环境变量
load_dotenv()


# 获取OpenAI API密钥
api_key = os.getenv("DEEPSEEK_API_KEY")

# 初始化OpenAI客户端
client = OpenAI(api_key=api_key,base_url="https://api.deepseek.com")

            
# 初始化OpenAI客户端
#client = OpenAI(api_key=api_key,http_client=None)

   # 添加一个简单的API调用测试
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)
print(response.choices[0].message.content)