from openai import OpenAI
from dotenv import load_dotenv
import os
# 加载环境变量
load_dotenv()


api_key = os.getenv("OPENAI_API_KEY")

            
# 初始化OpenAI客户端
client = OpenAI(api_key=api_key,http_client=None)

   # 添加一个简单的API调用测试
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
           {"role": "user", "content": "你好，世界！"}
       ]
   )
print(response.choices[0].message.content)