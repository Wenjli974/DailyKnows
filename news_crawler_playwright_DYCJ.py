from playwright.sync_api import sync_playwright
from datetime import datetime
import docx
from PIL import Image
import pytesseract
import os
import time
import cv2
import numpy as np
import json

def preprocess_image_for_ocr(image_path):
    # 读取图片
    img = cv2.imread(image_path)
    
    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 自适应阈值处理，提高文字与背景的对比度
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # 降噪
    denoised = cv2.fastNlMeansDenoising(binary)
    
    # 保存预处理后的图片
    processed_path = f"processed_{os.path.basename(image_path)}"
    cv2.imwrite(processed_path, denoised)
    
    return processed_path

def extract_text_from_image(image_path):
    # 预处理图片
    processed_path = image_path
    #preprocess_image_for_ocr(image_path)
    
    try:
        # 使用OCR提取文字
        text = pytesseract.image_to_string(
            Image.open(processed_path),
            lang='chi_sim',
            config='--psm 1 --oem 3'  # PSM 1: 自动页面分割并进行OSD
        )
        
        # 删除预处理的临时文件
        os.remove(processed_path)
        
        return text
    except Exception as e:
        print(f"OCR处理出错: {str(e)}")
        if os.path.exists(processed_path):
            os.remove(processed_path)
        return ""

def get_news_links(page, url, news_count=3):
    page.goto(url)
    page.wait_for_load_state('networkidle')
    
    # 获取新闻链接
    links = page.evaluate(f"""
    () => {{
        return Array.from(document.querySelectorAll('a')).filter(a => {{
            const text = a.textContent.trim();
            const href = a.href;
            return text.length > 15 && href.includes('yicai.com') && !href.endsWith('/');
        }}).slice(0, {news_count}).map(a => ({{ 
            href: a.href, 
            text: a.textContent.trim() 
        }}));
    }}
    """)
    print(f"从 {url} 获取到的链接：", links)
    return links

def capture_article_content(page, url, index):
    try:
        print(f"正在等待文章内容加载...")
        page.goto(url, wait_until='networkidle', timeout=3000)
        
        # 等待文章主体加载，使用多个可能的选择器
        # selectors = [
        #     '.article-content',
        #     '#article-content',
        #     '.article-text',
        #     '.article-body',
        #     'article'
        # ]
        
        # article_content = None
        # for selector in selectors:
        #     try:
        #         article_content = page.wait_for_selector(selector, timeout=5000)
        #         print(f"找到内容选择器: {selector}")
        #         break
        #     except:
        #         continue
        
        # if not article_content:
        #     print("未找到文章内容选择器，尝试使用备用方法")
        #     # 如果找不到特定选择器，尝试获取页面主体
        article_content = page.locator('body')
        
        # 尝试获取标题
        title_selectors = [
            '.article-title',
            '#article-title',
            'h1',
            '.title'
        ]
        
        title = None
        for selector in title_selectors:
            try:
                title_element = page.wait_for_selector(selector, timeout=5000)
                title = title_element.text_content().strip()
                print(f"获取到标题: {title}")
                break
            except:
                continue
        
        if not title:
            title = "无法获取标题"
            print("获取标题失败")
        
        # 确保页面完全加载
        page.wait_for_load_state('networkidle')
        #time.sleep(2)  # 额外等待时间
        
        # 截图部分 - 无论是否成功获取内容都进行截图
        full_page_path = f"D:/pythonProject/DailyKnows/img/news_{index}_full_{datetime.now().strftime('%H%M%S')}.png"
        page.screenshot(path=full_page_path, full_page=True)
        print(f"保存整页截图: {full_page_path}")
        
        content_path = None
        if article_content:
            # 如果找到了内容区域，截取该区域
            content_path = f"D:/pythonProject/DailyKnows/img/news_{index}_content_{datetime.now().strftime('%H%M%S')}.png"
            article_content.screenshot(path=content_path)
            print(f"保存文章区域截图: {content_path}")
        
        # 先尝试从DOM获取内容
        try:
            content_text = ""
            if article_content:
                content_text = article_content.text_content().strip()
            
            # 如果成功获取内容且长度合理，直接返回
            if content_text and len(content_text) > 100:
                print("通过DOM成功提取文章内容")
                return title, content_text, full_page_path, content_path
            else:
                print("DOM提取内容为空或过短，尝试OCR识别")
        except Exception as e:
            print(f"DOM提取内容失败: {str(e)}，尝试OCR识别")
        
        # DOM提取失败，尝试OCR识别
        print("正在从截图中提取文字...")
        if content_path:
            # 优先从内容区域截图提取
            content_text = extract_text_from_image(content_path)
            print(f"从内容截图提取的文字长度: {len(content_text)}")
            
            if not content_text.strip():
                print("内容区域OCR失败，尝试从整页截图提取...")
                content_text = extract_text_from_image(full_page_path)
                print(f"从整页截图提取的文字长度: {len(content_text)}")
        else:
            # 直接从整页截图提取
            content_text = extract_text_from_image(full_page_path)
            print(f"从整页截图提取的文字长度: {len(content_text)}")
        
        return title, content_text, full_page_path, content_path
    except Exception as e:
        print(f"Error capturing content: {str(e)}")
        # 尝试至少保存整页截图
        try:
            full_page_path = f"img/news_{index}_full_error_{datetime.now().strftime('%H%M%S')}.png"
            page.screenshot(path=full_page_path, full_page=True)
            print(f"保存错误页面截图: {full_page_path}")
            # 尝试从错误页面截图中提取文字
            content_text = extract_text_from_image(full_page_path)
            if "新闻排行" in content_text:
                content_text = content_text.split("新闻排行")[0].strip()
            return "无法获取标题", content_text, full_page_path, None
        except:
            return "无法获取标题", "无法获取内容", None, None

def format_content(content):
    # 清理和格式化提取的文本
    lines = content.split('\n')
    # 移除空行和只包含空格的行
    lines = [line.strip() for line in lines if line.strip()]
    # 移除可能的OCR错误产生的特殊字符
    lines = [line for line in lines if len(line) > 1]  # 移除单字符行
    return '\n'.join(lines)

def create_news_report():
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f'D:/pythonProject/DailyKnows/materials/Local_news_{date_str}.json'
    
    # 检查今日的JSON文件是否存在
    json_data = []
    if os.path.exists(filename):
        print(f"发现今日文档: {filename}，将在其中追加新闻")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            # 获取最后一条新闻的ID
            last_id = max([item.get("id", 0) for item in json_data]) if json_data else 0
        except Exception as e:
            print(f"读取现有JSON文件出错: {str(e)}")
            last_id = 0
    else:
        print(f"未发现今日文档，将创建新文件: {filename}")
        last_id = 0
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)  # 设置headless=True来隐藏浏览器窗口
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # 要爬取的页面列表及对应的新闻数量
            urls_config = [
                #{"url": "https://www.yicai.com/", "count": 5},  # 首页5条
                {"url": "https://www.yicai.com/news/quanqiushichang/", "count": 2},  # 全球市场3条
                {"url": "https://www.yicai.com/news/shijie/", "count": 2}  # 世界新闻2条
            ]
            
            all_links = []
            # 从每个页面获取新闻链接
            for config in urls_config:
                url = config["url"]
                count = config["count"]
                links = get_news_links(page, url, count)
                all_links.extend(links)
                print(f"从 {url} 获取了 {len(links)} 条新闻链接")
            
            if not all_links:
                print("未获取到任何新闻链接！")
                return None
            
            # 记录已处理的链接，避免重复
            processed_urls = set()
            
            for i, link in enumerate(all_links, 1):
                # 避免重复处理同一链接
                if link['href'] in processed_urls:
                    print(f"跳过重复链接: {link['href']}")
                    continue
                
                processed_urls.add(link['href'])
                title, content, full_page_path, content_path = capture_article_content(page, link['href'], i)
                
                # 格式化文章内容
                formatted_content = format_content(content)
                
                # 添加新闻到JSON数据
                json_data.append({
                    "id": last_id + i,
                    "title": title,
                    "source": link["href"],
                    "content": formatted_content,
                })
                
        finally:
            browser.close()
    
    # 保存JSON文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n报告生成完成，包含 {len(processed_urls)} 条新闻")
    return filename

if __name__ == "__main__":
    # 设置Tesseract路径（根据实际安装路径修改）
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    try:
        filename = create_news_report()
        if filename:
            print(f"新闻报告已保存为：{filename}")
        else:
            print("报告生成失败！")
    except Exception as e:
        print(f"程序执行出错：{str(e)}") 