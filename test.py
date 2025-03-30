import os
import sys
import json
from datetime import datetime
import time
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取OpenAI API密钥
api_key = os.getenv("OPENAI_API_KEY")
print(api_key)
# 初始化OpenAI客户端
client = OpenAI(api_key=api_key)

response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "hi your name"},
            ],
            temperature=0.7,
            max_tokens=300
        )
print( response.choices[0].message.content.strip())