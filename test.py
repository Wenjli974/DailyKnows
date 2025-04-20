from openai import OpenAI
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import time
import json
# 加载环境变量
load_dotenv()


# 获取OpenAI API密钥
api_key = os.getenv("DEEPSEEK_API_KEY")

# 初始化OpenAI客户端
client = OpenAI(api_key=api_key,base_url="https://api.deepseek.com")
today = datetime.now()
yesterday = today - timedelta(days=1)
today_str = today.strftime("%Y%m%d")
yesterday_str = yesterday.strftime("%Y%m%d")
today_file = f'D:/pythonProject/DailyKnows/materials/Local_news_{today_str}.json'
yesterday_file = f'D:/pythonProject/DailyKnows/materials/Local_news_{yesterday_str}.json'
today_history_file = f'D:/pythonProject/DailyKnows/materials/Local_news_{today_str}_1.json'
    
    #读取yesterday_file和today_history_file 所有标题 拼接在一起，与今日文件内容进行查重
with open(yesterday_file, 'r', encoding='utf-8') as f:
        yesterday_news = json.load(f)
with open(today_history_file, 'r', encoding='utf-8') as f:
        today_history_news = json.load(f)
yesterday_titles = {news['title'] for news in yesterday_news}
today_history_titles = {news['title'] for news in today_history_news}
all_titles = yesterday_titles | today_history_titles
print(all_titles)
#打印一共有多少条新闻
print(len(all_titles))

            
# 初始化OpenAI客户端
#client = OpenAI(api_key=api_key,http_client=None)
# date_str = datetime.now().strftime("%Y%m%d")
# yesterday_date_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
# date_str_with_summary = f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}_with_summary.json'
# date_str_json = f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}.json'
# yesterday_date_str_with_summary = f'D:/pythonProject/DailyKnows/materials/Local_news_{yesterday_date_str}_with_summary.json'

# assistant_prompt = "以下是历史新闻标题，作为判断今日新闻主体是否在历史新闻中出现过的参考：\n"
# if os.path.exists(date_str_with_summary):
#             with open(date_str_with_summary, 'r', encoding='utf-8') as f:
#                 date_str_with_summary_data = json.load(f)
#             for news in date_str_with_summary_data:
#                 assistant_prompt += f"标题：{news['title']}\n"
        
# if os.path.exists(yesterday_date_str_with_summary):
#             with open(yesterday_date_str_with_summary, 'r', encoding='utf-8') as f:
#                 yesterday_date_str_with_summary_data = json.load(f)
#             for news in yesterday_date_str_with_summary_data:
#                 assistant_prompt += f"标题：{news['title']}\n"
# print(assistant_prompt)
#    # 添加一个简单的API调用测试
# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "assistant", "content": assistant_prompt},
#         {"role": "user", "content": "请你参考之前的新闻，判断下述新闻主体是否在历史新闻中出现过：虚假宣传自动驾驶可判2年。注意只需要回答是否，不需要其他解释"},
#     ],
#     stream=False
# )
# print(response.choices[0].message.content)

# from langchain_openai import ChatOpenAI
# from browser_use import Agent
# import asyncio
# from dotenv import load_dotenv
# import pandas as pd
# import json
# from docx import Document
# from docx.shared import Cm
# from datetime import datetime, timedelta
# import time

# load_dotenv()

# stock_list =["上汽集团", "比亚迪", "吉利汽车","长城汽车","长安汽车","赛力斯","广汽集团","北京汽车","江淮汽车","一汽解放","东风股份","上证指数","深证成指","理想汽车","蔚来","小鹏汽车","零跑汽车","华域汽车","一汽富维","宁德时代","潍柴动力","均胜电子","宁波华翔","拓普集团","国轩高科","中鼎股份","三花智控"]

# prompt = f"""
#     作为汽车行业CEO秘书，你工作严谨认真，你擅长进行数据核对和分析，你每天需要给老板汇报汽车行业主要公司的股价变价，
#     请你按照下述步骤完成任务：
#     1. 打开百度
#     2. 在百度中搜索今日{stock_list}中所有公司的股价和涨幅，
#     3. 输出格式Json：{{
#         "公司":<上汽集团>
#         "今日股价":<10.00>
#         "涨跌": <+1.00%>
#     }}
#     请注意：
#     1. 数据准确无误，请认真核对数据，请注意涨跌正负符号无误。
#     2. 请严格按格式输出，不要输出其他内容。
# """
# async def main():
#     agent = Agent(
#         task=prompt,
#         llm=ChatOpenAI(model="gpt-4o"),
#     )
#     history = await agent.run()
#     result = history.final_result()
#     print(result)
    
#     # 修复JSON格式
#     fixed_result = "[" + result + "]"
#     try:
#         # 尝试解析修复后的JSON
#         data = json.loads(fixed_result)
#     except json.JSONDecodeError:
#         # 如果仍然无法解析，使用自定义方法解析
#         data = []
#         # 分割多个记录
#         stock_entries = result.split('},{')
#         for entry in stock_entries:
#             # 清理格式
#             entry = entry.replace('{', '').replace('}', '')
#             lines = entry.strip().split(',')
#             stock_data = {}
#             for line in lines:
#                 if ':' in line:
#                     key, value = line.split(':', 1)
#                     key = key.strip().strip('"')
#                     value = value.strip().strip('"')
#                     stock_data[key] = value
#             if stock_data:
#                 data.append(stock_data)
    
#     # 创建Word文档
#     doc = Document()
    
#     # 添加标题
#     doc.add_heading('汽车行业股价报告', 0)
    
#     # 创建表格
#     table = doc.add_table(rows=1, cols=3)
#     table.style = 'Table Grid'
    
#     # 设置表头
#     hdr_cells = table.rows[0].cells
#     hdr_cells[0].text = '公司'
#     hdr_cells[1].text = '今日股价'
#     hdr_cells[2].text = '涨跌'
    
#     # 添加数据行
#     for item in data:
#         row_cells = table.add_row().cells
#         row_cells[0].text = item.get('公司', '')
#         row_cells[1].text = item.get('今日股价', '')
#         row_cells[2].text = item.get('涨跌', '')
    
#     date_str = datetime.now().strftime("%Y-%m-%d")
#     # 保存文档
#     doc.save(f'汽车行业股价报告_{date_str}.docx')
#     print(f"表格已保存至'汽车行业股价报告_{date_str}.docx'")

# asyncio.run(main())