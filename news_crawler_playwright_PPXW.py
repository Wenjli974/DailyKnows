import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 从环境变量中获取OpenAI API密钥
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key,http_client=None)

async def extract_news_content(page, url):
    """提取新闻页面的正文内容"""
    try:
        # 设置超时时间为30秒
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=30000)
        
        # 提取新闻正文内容 - 根据澎湃新闻的页面结构调整选择器
        content = await page.evaluate("""
        () => {
            // 尝试不同的选择器来获取新闻正文
            const contentSelectors = [
                '.news_txt', // 常见的新闻正文选择器
                '.content', 
                '.article-content',
                '.video_txt',
                '.news_part_limit'
            ];
            
            for (const selector of contentSelectors) {
                const element = document.querySelector(selector);
                if (element) {
                    return element.innerText.trim();
                }
            }
            
            // 如果所有选择器都失败，尝试获取主要内容区域
            const mainContent = document.querySelector('main') || document.querySelector('article');
            if (mainContent) {
                return mainContent.innerText.trim();
            }
            
            return ""; // 返回空字符串而不是错误消息
        }
        """)
        
        if content:
            return content
        else:
            print(f"  警告: 无法找到新闻内容 - {url}")
            return ""
    except Exception as e:
        print(f"  错误: 提取新闻内容失败 - {url} - {str(e)}")
        return ""  # 返回空字符串表示提取失败

async def main():
    # 打开浏览器并导航到澎湃新闻
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("正在打开澎湃新闻...")
        await page.goto("https://www.thepaper.cn/")
        await page.wait_for_load_state("networkidle")
        
        # 提取所有新闻内容
        news_items = await page.evaluate("""
        () => {
            const newsItems = [];
            const seenLinks = new Set();
            
            // 获取页面上的所有链接
            const allLinks = document.querySelectorAll('a');
            
            for (const link of allLinks) {
                const href = link.getAttribute('href');
                const title = link.textContent.trim();
                
                // 检查是否是有效的新闻链接（以"/newsDetail_forward_"开头的相对路径）
                if (href && 
                    href.includes('/newsDetail_forward_') && 
                    title && 
                    title.length > 5 && 
                    !seenLinks.has(href)) {
                    
                    // 将相对链接转为绝对链接
                    const fullLink = href.startsWith('http') ? href : `https://www.thepaper.cn${href}`;
                    seenLinks.add(href);
                    
                    newsItems.push({
                        title: title,
                        link: fullLink
                    });
                }
            }
            
            return newsItems;
        }
        """)
        
        print(f"共提取到 {len(news_items)} 条新闻")
         # 准备输入给大模型的文本
        news_list_text = "\n".join([f"{i+1}. {item['title']} - {item['link']}" for i, item in enumerate(news_items)])
        print(news_list_text)
        # 使用大模型挑选最重要的5条新闻
        selection_criteria = f"""你是一个新闻分析助手，擅长判断新闻重要性，侧重于时政新闻和社会热点新闻
        请从以下新闻列表中选出最重要的8条新闻，判断角度如下：
        1. 政策影响和宏观经济方向
        2. 综合社会影响力和时事热点内容
        3. 国际关系和贸易形势
        
        注意：
        1.涉及国家领导人的活动和发言的新闻不需要选出！
        2.请保证挑选出的新闻在内容上具有代表性，不要挑选重复的新闻。
        
        新闻列表:
        {news_list_text}

        返回格式必须是一个JSON对象，包含selected_news数组，每个新闻项包含:
        {{
          "selected_news": [
            {{
              "id": 1,
              "title": "新闻标题",
              "source": "新闻链接",
            }},
            {{
              "id": 2,
              "title": "新闻标题",
              "source": "新闻链接",
            }}
          ]
        }}
        只需返回JSON，不要有其他文字。
        """
        
       
        try:
            print("正在使用大模型分析新闻重要性...")
            response = client.chat.completions.create(
                model="gpt-4o", # 或其他可用的模型
                messages=[
                    {"role": "system", "content": "你是一个新闻分析助手，擅长判断新闻重要性。"},
                    {"role": "user", "content": selection_criteria}
                ],
                response_format={"type": "json_object"}
            )
            
            # 解析大模型返回的JSON
            result_text = response.choices[0].message.content
            try:
                result_json = json.loads(result_text)
                if "selected_news" in result_json:
                    important_news = result_json["selected_news"]
                else:
                    # 如果没有selected_news键，假设直接返回了数组
                    important_news = result_json
                
                # 爬取每条重要新闻的内容
                print("\n正在爬取重要新闻的详细内容...")
                for news in important_news:
                    news_link = news.get('link') or news.get('source')  # 兼容不同的字段名
                    if news_link:
                        print(f"正在爬取: {news.get('title', '未知标题')}")
                        try:
                            content = await extract_news_content(page, news_link)
                            # 将内容添加到新闻对象中
                            news['content'] = content
                            # 如果成功获取到内容，添加内容长度提示
                            if content:
                                print(f"  成功: 内容长度 {len(content)} 字符")
                            else:
                                print(f"  警告: 未获取到内容")
                        except Exception as e:
                            print(f"  错误: 处理新闻时发生异常 - {str(e)}")
                            news['content'] = ""  # 设置为空内容
                    else:
                        print(f"  警告: 新闻链接缺失 - {news.get('title', '未知标题')}")
                        news['content'] = ""
                
                # 生成日期字符串用于文件名
                date_str = datetime.now().strftime("%Y%m%d")
                local_file = f"D:/pythonProject/DailyKnows/materials/Local_news_{date_str}.json"
                
                # 检查文件是否已存在
                if os.path.exists(local_file):
                    # 如果文件存在，读取现有内容并追加
                    with open(local_file, "r", encoding="utf-8") as f:
                        try:
                            existing_data = json.load(f)
                            
                            # 查找已有新闻中的最大id
                            max_id = 0
                            
                            # 根据文件结构处理
                            if isinstance(existing_data, list):
                                # 如果是数组，直接遍历
                                for item in existing_data:
                                    if isinstance(item, dict) and 'id' in item:
                                        max_id = max(max_id, int(item['id']))
                            else:
                                # 如果是对象且有news字段
                                if "news" in existing_data and isinstance(existing_data["news"], list):
                                    for item in existing_data["news"]:
                                        if isinstance(item, dict) and 'id' in item:
                                            max_id = max(max_id, int(item['id']))
                            
                            print(f"找到已有新闻最大id: {max_id}")
                            
                            # 为新闻分配新id
                            for i, news in enumerate(important_news):
                                news['id'] = max_id + i + 1
                            
                            # 追加到现有数据
                            if isinstance(existing_data, list):
                                existing_data.extend(important_news)
                                save_data = existing_data
                            else:
                                # 如果文件包含对象，假设它有一个news数组
                                if "news" in existing_data:
                                    # 将news键下的数组与新数据合并，并直接保存为数组
                                    combined_news = existing_data["news"] + important_news
                                    save_data = combined_news
                                else:
                                    # 如果没有news键但是对象，创建新数组
                                    save_data = important_news
                                
                        except json.JSONDecodeError:
                            # 如果文件损坏，创建新内容
                            print("文件格式错误，创建新内容")
                            # 为新闻分配id从1开始
                            for i, news in enumerate(important_news):
                                news['id'] = i + 1
                            # 直接保存为数组，不使用news键
                            save_data = important_news
                else:
                    # 如果文件不存在，创建新内容
                    print("文件不存在，创建新内容")
                    # 为新闻分配id从1开始
                    for i, news in enumerate(important_news):
                        news['id'] = i + 1
                    # 直接保存为数组，不使用news键
                    save_data = important_news
                
                # 保存结果到文件
                with open(local_file, "w", encoding="utf-8") as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                # 打印结果
                print(f"\n今日重要新闻(已保存到 {local_file}):")
                for news in important_news:
                    print(f"{news.get('id', '-')}. {news.get('title', '未知标题')}")
                    print(f"   链接: {news.get('link', news.get('source', '未知链接'))}")
                    print(f"   内容长度: {len(news.get('content', ''))} 字符")
                    print()

                
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"返回的内容: {result_text}")
        
        except Exception as e:
            print(f"分析新闻时出错: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 关闭浏览器
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
