import asyncio
from playwright.async_api import async_playwright
import time
import re
import os
from PIL import Image
import pytesseract
import io
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 从环境变量中获取OpenAI API密钥
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key, http_client=None)

# 设置Tesseract路径 - 请根据您的实际安装路径修改
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # 常见默认路径
# 如果上面的路径不对，请修改为您的实际安装路径，例如：
# pytesseract.pytesseract.tesseract_cmd = r'D:\Program Files\Tesseract-OCR\tesseract.exe'

# OCR文本识别函数
def extract_text_from_image(image_path):
    try:
        # 使用pytesseract进行OCR识别
        image = Image.open(image_path)
        # 可以设置为简体中文语言
        text = pytesseract.image_to_string(image, lang='chi_sim')
        return text
    except Exception as e:
        print(f"OCR识别出错: {e}")
        return "OCR识别失败"

# 从页面获取新闻列表
async def get_news_from_page(page):
    print("正在从盖世汽车网站获取新闻...")
    
    # 截图保存，便于调试
    screenshot_path = "img/gasgoo_page.png"
    await page.screenshot(path=screenshot_path)
    print(f"已保存盖世汽车网页截图到 {screenshot_path}")
    
    # 使用JavaScript提取页面所有新闻链接
    links = await page.evaluate('''() => {
        const newsLinks = [];
        const seenLinks = new Set();
        
        // 获取页面上的所有链接
        const allLinks = document.querySelectorAll('a');
        
        for (const link of allLinks) {
            const text = link.innerText.trim();
            const href = link.getAttribute('href');
            
            // 确保链接有标题且不是JavaScript链接
            if (text && text.length > 5 && href && !href.includes('javascript:') && !seenLinks.has(href)) {
                // 判断标题是否像新闻标题（不包含菜单项等）
                const isNewsTitle = text.length > 10 && 
                                   !text.includes('登录') && 
                                   !text.includes('注册') &&
                                   !text.includes('Gasgoo night') &&
                                   !text.includes('首页');
                
                if (isNewsTitle) {
                    seenLinks.add(href);
                    
                    // 构建完整URL
                    const fullLink = href.startsWith('http') ? href : `https://auto.gasgoo.com${href}`;
                    
                    newsLinks.push({
                        title: text,
                        url: fullLink
                    });
                }
            }
        }
        
        // 返回找到的新闻链接
        return newsLinks;
    }''')
    
    print(f"共找到 {len(links)} 条盖世汽车新闻")
    return links

# 从新闻URL获取内容
async def get_news_content(context, news_data):
    final_news_data = []
    for i, news in enumerate(news_data):
        if not news['url']:
            continue
            
        print(f"\n正在访问第 {i+1} 篇新闻: {news['url']}")
        
        # 打开新闻页面
        news_page = await context.new_page()
        try:
            await news_page.goto(news['url'], timeout=50000)
            await news_page.wait_for_load_state('domcontentloaded')
            #等待2s
            await asyncio.sleep(2)
            
            # 截图保存整个页面
            content_screenshot_path = f"img/gasgoo_news_{i+1}_content.png"
            
            # 尝试找到内容区域并截图
            content_area = await news_page.query_selector('.article-content, .content, .article-body, .main-content')
            if content_area:
                await content_area.screenshot(path=content_screenshot_path)
                print(f"已保存文章内容区域截图到 {content_screenshot_path}")
            else:
                # 如果找不到特定区域，截取整个页面
                await news_page.screenshot(path=content_screenshot_path, full_page=True)
                print(f"已保存整个页面截图到 {content_screenshot_path}")
            
            # 先尝试通过DOM提取内容
            content = await news_page.evaluate('''() => {
                // 尝试查找可能的文章内容容器
                const selectors = [
                    '.article-content', '.content', '.article-body', '.main-content',
                    '.article', '.news-content', '.detail-content', '.detail'
                ];
                
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element && element.innerText.length > 100) {
                        // 清理内容，去除多余空白
                        return element.innerText
                            .replace(/\\s+/g, ' ')
                            .replace(/\\n+/g, '\\n')
                            .trim();
                    }
                }
                
                // 如果找不到指定选择器，尝试找最长的p标签集合
                const paragraphs = document.querySelectorAll('p');
                if (paragraphs.length > 0) {
                    let content = '';
                    for (const p of paragraphs) {
                        if (p.innerText.length > 20) {
                            content += p.innerText + '\\n';
                        }
                    }
                    if (content.length > 100) {
                        return content.trim();
                    }
                }
                
                return "";  // 返回空字符串表示提取失败
            }''')
            
            # 如果DOM提取失败，尝试OCR识别
            if not content or len(content.strip()) < 100:
                print("DOM提取内容失败，尝试OCR识别...")
                # 使用OCR识别截图中的文本
                content = extract_text_from_image(content_screenshot_path)
                if content and len(content.strip()) > 100:
                    print("OCR识别成功")
                else:
                    content = "无法提取内容"
            
            # 准备JSON数据
            json_item = {
                "id": i + 1,
                "title": news['title'],
                "source": news['url'],
                "content": content
            }
            final_news_data.append(json_item)
            
        except Exception as e:
            print(f"访问新闻时出错: {e}")
            json_item = {
                "id": i + 1,
                "title": news['title'],
                "source": news['url'],
                "content": f"访问出错: {str(e)}"
            }
            final_news_data.append(json_item)
        finally:
            await news_page.close()
    
    return final_news_data

# 保存新闻数据为JSON
def save_news_to_json(final_news_data):
    # 生成当日日期格式
    today = datetime.now().strftime("%Y%m%d")
    json_filename = f"D:/pythonProject/DailyKnows/materials/Local_news_{today}.json"
    
    # 检查文件是否存在
    if os.path.exists(json_filename):
        # 如果文件存在，读取现有内容并追加
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # 获取现有数据中的最大ID
            max_id = 0
            for item in existing_data:
                if item.get('id', 0) > max_id:
                    max_id = item['id']
            
            # 更新新数据的ID
            for item in final_news_data:
                max_id += 1
                item['id'] = max_id
            
            # 合并数据
            combined_data = existing_data + final_news_data
            
            # 保存合并后的数据
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, ensure_ascii=False, indent=4)
            
            print(f"\n已将新闻数据追加到: {json_filename}")
        
        except Exception as e:
            print(f"读取或更新JSON文件时出错: {e}")
            # 如果出错，作为新文件写入
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(final_news_data, f, ensure_ascii=False, indent=4)
            print(f"\n已将新闻数据保存到: {json_filename}")
    else:
        # 如果文件不存在，直接创建新文件
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(final_news_data, f, ensure_ascii=False, indent=4)
        print(f"\n已将新闻数据保存到: {json_filename}")

async def main(news_count=8):
    """
    主函数：从盖世汽车网站获取新闻
    
    参数:
    news_count: 获取的新闻数量
    """
    async with async_playwright() as p:
        # 启动浏览器
        print("正在启动浏览器...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900}
        )
        
        # 确保图片目录存在
        os.makedirs("img", exist_ok=True)
        
        try:
            # 打开盖世汽车网页
            page = await context.new_page()
            print("正在打开盖世汽车网站...")
            await page.goto('https://auto.gasgoo.com/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_load_state('networkidle')
                
            # 获取新闻列表
            news_list = await get_news_from_page(page)
            print(news_list)
            print(f"从盖世汽车网站获取了 {len(news_list)} 条新闻")
            
            # 准备输入给大模型的文本
            news_list_text = "\n".join([f"{i+1}. {item['title']} - {item['url']}" for i, item in enumerate(news_list)])
            
            # 使用大模型挑选最重要的新闻
            selection_criteria = f"""你是一个汽车行业新闻分析助手，擅长判断汽车行业新闻重要性。
            请从以下汽车行业新闻列表中选出最重要的{news_count}条新闻，判断角度如下：
            1. 国内政策及新闻通知
            2. 汽车行业重要新闻
            3. 企业重大动向
            4. 市场营销战略
            5. 国际汽车行业发展趋势
            
            注意：请保证挑选出的新闻在内容上具有代表性，不要挑选重复的新闻。

            新闻列表:
            {news_list_text}

            返回格式必须是一个JSON对象，包含selected_news数组，每个新闻项包含:
            {{
              "selected_news": [
                {{
                  "id": 1,
                  "title": "新闻标题",
                  "url": "新闻链接",
                }},
                {{
                  "id": 2,
                  "title": "新闻标题",
                  "url": "新闻链接",
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
                        {"role": "system", "content": "你是一个汽车行业新闻分析助手，擅长判断汽车新闻重要性。"},
                        {"role": "user", "content": selection_criteria}
                    ],
                    response_format={"type": "json_object"}
                )
                
                # 解析大模型返回的JSON
                result_text = response.choices[0].message.content
                result_json = json.loads(result_text)
                
                if "selected_news" in result_json:
                    important_news = result_json["selected_news"]
                else:
                    # 如果没有selected_news键，假设直接返回了数组
                    important_news = result_json
                
                print(f"\n大模型选择了 {len(important_news)} 条重要新闻")
                
                # 获取每条重要新闻的内容
                news_content = await get_news_content(context, important_news)
                
                # 输出结果摘要
                print("\n===== 新闻总结 =====")
                for i, news in enumerate(news_content):
                    print(f"\n新闻 {i+1}:")
                    print(f"标题: {news['title']}")
                    print(f"URL: {news['source']}")
                    
                    # 只显示内容的前200个字符
                    #content_preview = news.get('content', '')[:200] + '...' if len(news.get('content', '')) > 200 else news.get('content', '')
                    #print(f"内容预览: {content_preview}")
                
                # 保存新闻数据
                save_news_to_json(news_content)
                
            except Exception as e:
                print(f"分析新闻时出错: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"运行过程中出错: {e}")
        
        finally:
            # 关闭浏览器
            print("正在关闭浏览器...")
            await context.close()
            await browser.close()

if __name__ == "__main__":
    # 设置获取的新闻数量
    news_count = 8  # 获取的新闻数量
    asyncio.run(main(news_count))
