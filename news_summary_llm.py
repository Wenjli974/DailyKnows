#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新闻总结脚本 - 使用OpenAI GPT-4o模型对新闻内容进行总结和分类
"""

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

# 初始化OpenAI客户端
client = OpenAI(api_key=api_key)

def summarize_news(title, content):
    """
    使用GPT-4o模型对新闻进行总结和分类
    返回JSON格式结果，包含总结和标签
    """
    try:
        # 清理内容文本，移除多余的空格和特殊字符
        cleaned_content = ' '.join(content.split())
        
        # 截断过长的内容以避免超出token限制
        max_content_length = 5000  # 设置一个合理的长度限制
        if len(cleaned_content) > max_content_length:
            cleaned_content = cleaned_content[:max_content_length] + "..."
        
        user_prompt = f"""你是一个专业的新闻分析助手，擅长在新闻原文中提炼总结新闻内容,反应新闻的中心思想同时保留重要细节信息.
        请对以下新闻进行总结和分类:
        
        标题：{title}
        内容：{cleaned_content}
        
        要求：
        1. 总结：用8句话以内对新闻进行提炼总结，忠于原文，保留重点信息(尤其是政策类描述,数字相关描述).
        2. 标签：从以下选项中选择最合适的一个标签："中国新闻"，"国际新闻"，"汽车相关"
        3. 网站：从以下选项中选择最合适的一个网站："新华网"，"人民日报"，"第一财经"
        以下是你需要输出的JSON格式：
        {{
            "总结": "这里是新闻总结内容",
            "标签": "这里是新闻标签",
            "网站": "这里是新闻来源网站"
        }}
        
        请只输出JSON格式，不要有任何其他文字说明。
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一个专业的新闻分析AI助手，擅长新闻内容总结和分类。请以JSON格式输出结果。"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content.strip()
        # 解析JSON字符串为Python字典，然后再转回JSON字符串，确保格式正确
        return json.loads(result)
    except Exception as e:
        print(f"生成摘要和标签时出错：{e}")
        return {"总结": f"生成摘要时出错：{e}", "标签": "未知"}

def process_news_file():
    """
    处理新闻JSON文件，为每条新闻添加摘要和标签
    """
    date_str = datetime.now().strftime("%Y%m%d")
    file_path = f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}.json'

    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            news_data = json.load(f)
        
        # 为每条新闻生成摘要和标签
        print(f"正在处理 {len(news_data)} 条新闻...")
        for news in news_data:
            print(f"处理新闻ID: {news['id']}, 标题: {news['title']}")
            result = summarize_news(news['title'], news['content'])
            news['summary'] = result["总结"]
            news['category'] = result["标签"]
            news['web'] = result["网站"]
        
        # 保存结果到文件
        output_file =f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}_with_summary.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=4)
        
        print(f"处理完成，结果已保存至 {output_file}")
        return news_data
    
    except Exception as e:
        print(f"处理文件时出错：{e}")
        return None

if __name__ == "__main__":
    process_news_file()

