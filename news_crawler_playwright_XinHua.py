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
async def get_news_from_page(page, news_count, page_name, selector_strategy="default"):
    print(f"正在从{page_name}获取新闻...")
    
    # 截图保存，便于调试
    screenshot_path = f"img/{page_name}_page.png"
    await page.screenshot(path=screenshot_path)
    print(f"已保存{page_name}截图到 {screenshot_path}")
    
    links = []
    
    if selector_strategy == "homepage":
        # 首页的新闻提取逻辑
        precise_links = await page.evaluate('''() => {
            // 尝试找到首页右下角的新闻列表
            const newsContainers = document.querySelectorAll('.right-box ul, .news-list ul, .listBox ul, .list ul, .box ul');
            let rightBottomNewsList = null;
            
            // 查找位于页面右下方的新闻列表容器
            for (const container of newsContainers) {
                const rect = container.getBoundingClientRect();
                const rightSide = rect.right > window.innerWidth * 0.8;
                const bottomHalf = rect.top > window.innerHeight * 0.6;
                const hasLinkItems = container.querySelectorAll('li a').length > 0;
                
                if (rightSide && bottomHalf && hasLinkItems) {
                    rightBottomNewsList = container;
                    break;
                }
            }
            
            // 如果找到右下角新闻列表，提取其中的链接
            if (rightBottomNewsList) {
                const newsLinks = [];
                const links = rightBottomNewsList.querySelectorAll('li a');
                
                for (const link of links) {
                    const text = link.innerText.trim();
                    const href = link.getAttribute('href');
                    
                    // 添加标题长度检查，确保标题长度大于7个字
                    if (text && text.length > 7 && href && !href.includes('javascript:')) {
                        newsLinks.push({
                            text: text,
                            href: href,
                            position: link.getBoundingClientRect()
                        });
                    }
                }
                
                console.log(`从右下角列表中找到${newsLinks.length}条新闻`);
                return newsLinks;
            }
            
            // 如果没有找到特定的新闻列表，返回空数组
            return [];
        }''')
        
        if precise_links and len(precise_links) > 0:
            print(f"成功从{page_name}右下角新闻列表中找到 {len(precise_links)} 条新闻")
            links = precise_links
    
    elif selector_strategy == "auto":
        # 汽车频道的新闻提取逻辑
        auto_links = await page.evaluate('''() => {
            // 尝试找到汽车频道的新闻列表，特别关注页面中间位置
            const viewportHeight = window.innerHeight;
            const viewportWidth = window.innerWidth;
            
            // 定义页面中间区域
            const middleTop = viewportHeight * 0.25;
            const middleBottom = viewportHeight * 0.75;
            const middleLeft = viewportWidth * 0.25;
            const middleRight = viewportWidth * 0.75;
            
            // 所有可能包含新闻的容器
            const newsContainers = document.querySelectorAll('.news-list, .news-box, main, .listBox, .list');
            const newsLinks = [];
            
            // 从容器中提取链接，优先选择位于中间区域的
            for (const container of newsContainers) {
                const rect = container.getBoundingClientRect();
                
                // 检查容器是否位于中间区域（至少部分重叠）
                const isInMiddle = rect.bottom >= middleTop && 
                                  rect.top <= middleBottom &&
                                  rect.right >= middleLeft && 
                                  rect.left <= middleRight;
                
                if (isInMiddle) {
                    const links = container.querySelectorAll('a');
                    
                    for (const link of links) {
                        const linkRect = link.getBoundingClientRect();
                        const linkText = link.innerText.trim();
                        const href = link.getAttribute('href');
                        
                        // 检查链接自身是否在中间区域
                        const linkInMiddle = linkRect.bottom >= middleTop && 
                                           linkRect.top <= middleBottom &&
                                           linkRect.right >= middleLeft && 
                                           linkRect.left <= middleRight;
                        
                        if (linkText && href && !href.includes('javascript:') && linkText.length > 5) {
                            newsLinks.push({
                                text: linkText,
                                href: href,
                                isInMiddle: linkInMiddle // 添加位置标记
                            });
                        }
                    }
                }
            }
            
            // 也尝试查找有日期的新闻项（通常是新闻列表）
            const datePattern = /\d{4}-\d{2}-\d{2}/;
            const allLinks = document.querySelectorAll('a');
            for (const link of allLinks) {
                const linkRect = link.getBoundingClientRect();
                const isInMiddle = linkRect.bottom >= middleTop && 
                                 linkRect.top <= middleBottom &&
                                 linkRect.right >= middleLeft && 
                                 linkRect.left <= middleRight;
                
                // 检查自身或父元素是否包含日期
                const parent = link.parentElement;
                const hasDate = parent && datePattern.test(parent.innerText);
                
                if (hasDate) {
                    const text = link.innerText.trim();
                    const href = link.getAttribute('href');
                    
                    if (text && href && !href.includes('javascript:') && text.length > 5) {
                        newsLinks.push({
                            text: text,
                            href: href,
                            isInMiddle: isInMiddle // 添加位置标记
                        });
                    }
                }
            }
            
            // 优先返回在中间区域的链接
            newsLinks.sort((a, b) => {
                if (a.isInMiddle && !b.isInMiddle) return -1;
                if (!a.isInMiddle && b.isInMiddle) return 1;
                return 0;
            });
            
            return newsLinks;
        }''')
        
        if auto_links and len(auto_links) > 0:
            print(f"成功从{page_name}页面找到 {len(auto_links)} 条新闻")
            links = auto_links
    
    # 提取指定数量的有效新闻
    news_data = []
    for i, link in enumerate(links):
        if len(news_data) >= news_count:
            break
            
        title = link['text']
        url = link['href']
        
        
        # 确保URL是完整的
        if url and not url.startswith('http'):
            if url.startswith('//'):
                url = f'https:{url}'
            elif url.startswith('/'):
                url = f'https://www.xinhuanet.com{url}'
            else:
                url = f'https://www.xinhuanet.com/{url}'
        
        # 过滤无效URL
        if not re.match(r'^https?://', url):
            continue
            
        news_data.append({'title': title, 'url': url})
        print(f"找到{page_name}新闻 {len(news_data)}: {title}")
    
    return news_data

# 从新闻URL获取内容
async def get_news_content(context, news_data, start_index=0):
    final_news_data = []
    for i, news in enumerate(news_data):
        if not news['url']:
            continue
            
        print(f"\n正在访问第 {start_index+i+1} 篇新闻: {news['url']}")
        
        # 打开新闻页面
        news_page = await context.new_page()
        try:
            await news_page.goto(news['url'], timeout=50000)
            
            # 截图保存整个页面
            content_screenshot_path = f"img/news_{start_index+i+1}_content.png"
            
            # 尝试找到内容区域并截图
            content_area = await news_page.query_selector('.article, .content, #detail, .main-aticle, .main')
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
                    '.article', '.content', '.main-aticle', '#detail', 
                    '.article-body', '.main', '.center-part', '.article-content',
                    'p.text', '.text', '.textBody', '.main-content'
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
                "id": start_index + i + 1,
                "title": news['title'],
                "source": news['url'],
                "content": content
            }
            final_news_data.append(json_item)
            
        except Exception as e:
            print(f"访问新闻时出错: {e}")
            json_item = {
                "id": start_index + i + 1,
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
    
    # 检查文件夹是否存在，不存在则创建
    os.makedirs("materials", exist_ok=True)
    
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

async def main(homepage_news_count=5, auto_news_count=5):
    """
    主函数：从新华社首页和汽车频道获取新闻
    
    参数:
    homepage_news_count: 从首页获取的新闻数量
    auto_news_count: 从汽车频道获取的新闻数量
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
        
        all_news_data = []
        
        try:
            # 从首页获取新闻
            homepage_page = await context.new_page()
            
            print("正在打开新华社首页...")
            await homepage_page.goto('https://www.xinhuanet.com/home.htm', timeout=60000)
            await homepage_page.wait_for_load_state('domcontentloaded')
            await homepage_page.wait_for_load_state('networkidle')
                
            homepage_news = await get_news_from_page(
                homepage_page, 
                homepage_news_count, 
                "首页", 
                selector_strategy="homepage"
            )
            print(f"从首页获取了 {len(homepage_news)} 条新闻")
            # finally:
            #     await homepage_page.close()
            
            # 从汽车频道获取新闻
            auto_page = await context.new_page()

            print("正在打开汽车频道页面...")
            await auto_page.goto('https://www.news.cn/auto/gdxw/index.html', timeout=60000)
            await auto_page.wait_for_load_state('domcontentloaded')
            await auto_page.wait_for_load_state('networkidle')
                
            auto_news = await get_news_from_page(
                auto_page, 
                auto_news_count, 
                "汽车频道", 
                 selector_strategy="auto"
            )
            print(f"从汽车频道获取了 {len(auto_news)} 条新闻")

            
            # 获取所有新闻内容
            homepage_news_content = await get_news_content(context, homepage_news, 0)
            auto_news_content = await get_news_content(context, auto_news, len(homepage_news_content))
            
            # 合并所有新闻
            all_news_data = homepage_news_content + auto_news_content
            
            # 输出结果摘要
            print("\n===== 新闻总结 =====")
            for i, news in enumerate(all_news_data):
                print(f"\n新闻 {i+1}:")
                print(f"标题: {news['title']}")
                print(f"URL: {news['source']}")
                
                # 只显示内容的前200个字符
                content_preview = news.get('content', '')[:200] + '...' if len(news.get('content', '')) > 200 else news.get('content', '')
                print(f"内容预览: {content_preview}")
            
            # 保存新闻数据
            save_news_to_json(all_news_data)
            
        except Exception as e:
            print(f"运行过程中出错: {e}")
        
        finally:
            # 关闭浏览器
            print("正在关闭浏览器...")
            await context.close()
            await browser.close()

if __name__ == "__main__":
    # 参数化每个模块获取的新闻数量
    homepage_news_count = 5  # 从首页获取的新闻数量
    auto_news_count = 5      # 从汽车频道获取的新闻数量
    asyncio.run(main(homepage_news_count, auto_news_count)) 
