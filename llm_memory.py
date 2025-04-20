#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新闻总结脚本 - 使用OpenAI GPT-4o模型对新闻内容进行总结和分类
"""

import os
import sys
import json
from datetime import datetime, timedelta
import time
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取OpenAI API密钥
api_key = os.getenv("DEEPSEEK_API_KEY")

# 初始化OpenAI客户端
client = OpenAI(api_key=api_key,base_url="https://api.deepseek.com")


def summarize_news(title, content, source, today_news_title,history_titles):
    """
    使用GPT-4o模型对新闻进行总结和分类
    返回JSON格式结果，包含总结和标签
    """
    try:
        # 清理内容文本，移除多余的空格和特殊字符
        cleaned_content = ' '.join(content.split())
        #date_str = datetime.now().strftime("%Y%m%d")
        #yesterday_date_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        # 截断过长的内容以避免超出token限制
        max_content_length = 5000  # 设置一个合理的长度限制
        if len(cleaned_content) > max_content_length:
            cleaned_content = cleaned_content[:max_content_length] + "..."
        
        user_prompt = f"""你是一个专业的新闻分析助手，擅长在新闻原文中提炼总结新闻内容,反应新闻的中心思想同时保留重要细节信息.
        请对以下新闻进行总结和分类:
        
        标题：{title}
        来源：{source}
        内容：{cleaned_content}


        要求：
        1. 总结：请对新闻进行提炼总结，忠于原文，保留重点信息(关于政策类描述,数字量化描述,日期时间,注意需要保留！)
        2. 标签：请结合新闻的标题和内容，为新闻从以下选项中选择最合适的一个标签："中国新闻"，"汽车相关","国际新闻"，
        3. 网站：从以下选项中选择最合适的一个网站："澎湃新闻"，"人民日报"，"第一财经","盖世汽车"
        4. 是否在历史新闻中出现过：请先阅读分析你收到assistant中提供所有历史新闻的标题，判断当前新闻主题是否在历史新闻中出现过，如果出现过，则返回"是"，否则返回"否"。

        注意：
        1.新闻标签中：
        如果行动主体是中国/国内，则标签为"中国新闻"，
        如果包含汽车行业,提及汽车企业相关内容或者来源网站为盖世汽车,不管是国内/国外主体行为，均标签为"汽车相关", 
        如果行动主体是外国/国际且非汽车行业内容，则标签为"国际新闻"。

        2.网站需要参考来源URL中的信息：
        人民日报：http://paper.people.com.cn/
        第一财经：https://www.yicai.com/
        澎湃新闻：https://www.thepaper.cn/
        新华网：https://www.xinhuanet.com/ 或 https://www.news.cn/
        盖世汽车：https://auto.gasgoo.com/
        
        以下是你需要输出的JSON格式：
        {{
            "总结": "这里是新闻总结内容",
            "标签": "这里是新闻标签",
            "网站": "这里是新闻来源网站",
            "是否在历史新闻中出现过": "这里是判断结果"
        }}
        
        请只输出JSON格式，不要有任何其他文字说明。
        """

        assistant_prompt = "以下是需要的参考的历史新闻标题，请你作为判断当前新闻是否在历史新闻中出现过的参考：\n"
        
        assistant_prompt += f"{today_news_title}\n{history_titles}"

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的新闻分析AI助手，擅长新闻内容总结和分类。请以JSON格式输出结果。"},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
            stream=False,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content.strip()
        # 解析JSON字符串为Python字典，然后再转回JSON字符串，确保格式正确
        return json.loads(result)
    except Exception as e:
        print(f"生成摘要和标签时出错：{e}")
        return {"总结": f"生成摘要时出错：{e}", "标签": "未知"}

def check_duplicate_news():
    """
    检查当日新闻是否与昨日新闻重复
    以标题名称判断是否重复，如果重复则从当日文件中删除
    """
    # 获取当前日期和昨天日期

    date_str = datetime.now().strftime("%Y%m%d")
    yesterday_date_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    # 构建文件路径
    today_file = f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}.json'
    #昨日最新文件
    yesterday_file = f'D:/pythonProject/DailyKnows/materials/Local_news_{yesterday_date_str}.json'
    #今日历史文件
    today_history_file = f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}_1.json'
    try:
        #读取yesterday_file和today_history_file 所有标题 拼接在一起，与今日文件内容进行查重
        if os.path.exists(yesterday_file):
            with open(yesterday_file, 'r', encoding='utf-8') as f:
                yesterday_news = json.load(f)
        if os.path.exists(today_history_file):
            with open(today_history_file, 'r', encoding='utf-8') as f:
                today_history_news = json.load(f)
        history_titles = {news['title'] for news in yesterday_news} | {news['title'] for news in today_history_news}
    
        with open(today_file, 'r', encoding='utf-8') as f:
            today_news = json.load(f)

    #找出重复的新闻
        duplicate_count = 0
        unique_news = []
            
        for news in today_news:
            if news['title'] in history_titles:
                duplicate_count += 1
                print(f"发现重复新闻: {news['title']}")
            else:
                unique_news.append(news)
        
        # 如果有重复，更新今日文件
        if duplicate_count > 0:
            print(f"共发现 {duplicate_count} 条重复新闻，正在更新今日文件...")
            with open(today_file, 'w', encoding='utf-8') as f:
                json.dump(unique_news, f, ensure_ascii=False, indent=4)
            print(f"已从今日文件中删除 {duplicate_count} 条重复新闻")
            return history_titles
        else:
            print("没有发现重复新闻")
            return history_titles
            
    except Exception as e:
        print(f"检查重复新闻时出错：{e}")
        return history_titles
        

def process_news_file():
    """
    处理新闻JSON文件，为每条新闻添加摘要和标签
    """
    # 先检查并处理重复新闻
    history_titles = check_duplicate_news()
    print(history_titles)

    date_str = datetime.now().strftime("%Y%m%d")
    file_path = f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}.json'
    output_file =f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}_with_summary.json'
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            news_data = json.load(f)
        
        # 为每条新闻生成摘要和标签,每次生成都保存到json文件中
        print(f"正在处理 {len(news_data)} 条新闻...")
        error_count = 0
        today_news_title = ""
        for news in news_data:
            try:
                print(f"处理新闻ID: {news['id']}, 标题: {news['title']}")
                result = summarize_news(news['title'], news['content'], news['source'], today_news_title,history_titles)
                news['summary'] = result["总结"]
                news['category'] = result["标签"]
                news['web'] = result["网站"]
                news['is_duplicate'] = result["是否在历史新闻中出现过"]
                today_news_title += f"标题：{news['title']}\n"
            except Exception as e:
                error_count += 1
                print(f"处理新闻ID: {news['id']}时出错：{e}")
                # 标记需要检查的新闻
                news['summary'] = "生成摘要时出错，需要检查"
                news['category'] = "中国新闻"
                news['web'] = "check"
                news['is_duplicate'] = "否"
                today_news_title += f"标题：{news['title']}\n"


            #完成后输出
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=4)
        
        if error_count > 0:
            print(f"处理完成，有 {error_count} 条新闻需要检查。结果已保存至 {output_file}")
        else:
            print(f"处理完成，结果已保存至 {output_file}")
        return news_data
    
    except Exception as e:
        print(f"处理文件时出错：{e}")
        return None

if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "check_duplicate":
            print("开始检查重复新闻...")
            check_duplicate_news()
        else:
            print(f"未知命令: {sys.argv[1]}")
            print("可用命令: check_duplicate")
    else:
        # 默认执行全部流程
        process_news_file()

