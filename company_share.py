import os
import time
import pyautogui
import subprocess
import pyperclip  # 用于剪贴板操作
from datetime import datetime
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv
import pygetwindow as gw  # 用于获取窗口信息

# 加载环境变量
load_dotenv()

def capture_screen(filename=None, window_title="同花顺"):
    """截取同花顺窗口并保存"""
    if filename is None:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    try:
        # 查找同花顺窗口
        target_windows = [window for window in gw.getAllTitles() if window_title in window]
        if not target_windows:
            print(f"未找到包含'{window_title}'的窗口，将截取整个屏幕")
            screenshot = pyautogui.screenshot()
        else:
            # 使用找到的第一个匹配窗口
            window_name = target_windows[0]
            window = gw.getWindowsWithTitle(window_name)[0]
            
            # 激活窗口
            window.activate()
            time.sleep(0.5)  # 等待窗口激活
            
            # 获取窗口位置和大小
            left, top = window.left, window.top
            width, height = window.width, window.height
            
            # 截取指定窗口区域
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            print(f"已截取窗口: {window_name}")
    except Exception as e:
        print(f"截取窗口时出错: {e}，将截取整个屏幕")
        screenshot = pyautogui.screenshot()
    
    screenshot.save(filename)
    print(f"截图已保存为: {filename}")
    return filename

def open_tonghuashun_by_search():
    """通过Windows搜索打开同花顺应用"""
    try:
        # 按下Win键
        print("按下Win键打开搜索...")
        pyautogui.press('win')
        time.sleep(3)  # 增加等待时间确保搜索栏打开
        
        # 使用剪贴板输入中文
        print("搜索同花顺...")
        original_clipboard = pyperclip.paste()  # 保存当前剪贴板内容
        
        pyperclip.copy("同花顺")
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'v')  # 粘贴
        time.sleep(3)  # 等待搜索结果加载
        
        # 还原剪贴板内容
        pyperclip.copy(original_clipboard)
        
        # 按回车启动应用
        print("启动同花顺...")
        pyautogui.press('enter')
        
        # 等待应用启动
        print("等待同花顺启动...")
        time.sleep(8)  # 增加启动等待时间
        return True
    except Exception as e:
        print(f"启动同花顺时出错: {e}")
        return False

def analyze_stock_image(image_path):
    """
    使用GPT-4o分析图片并提取股票信息
    返回JSON格式的股票代码、名称、现价，涨跌额和涨跌幅
    """
    try:
        # 获取API密钥
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未找到OPENAI_API_KEY环境变量")
            
        # 初始化OpenAI客户端
        client = OpenAI()
        
        # 读取图片并转换为base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # 构建提示
        prompt = """ 你是一个资深的严谨的分析师，你可以通过图片中的股票信息，精准无误的提取出股票交易信息。
        请分析此图片中的共计27只股票表格信息，提取以下数据：
        1. 股票代码
        2. 股票名称
        3. 现价
        4. 涨跌额
        4. 涨幅（百分比）
        
        以JSON数组格式返回数据，每个股票一个对象，格式如下：
        [
            {   
                "id": "自增id",
                "code": "代码",
                "name": "名称",
                "price": "现价",
                "change_amount": "涨跌额",
                "change_percent": "涨幅"
            },
            ...
        ]

        注意：
        1. 请保证提取的信息内容完整真实正确，请确保每只股票的名称正确，数据正确，符号正确。
        2. 页面中股票如果为绿色，涨跌额和涨幅为负，如果为红色，涨跌额和涨幅为正，请保证输出的涨跌额和涨幅为正负符号正确
        3. 请保证JSON数据格式正确，不要有任何其他解释或文字。
        4. 重点：请认真检查你的结果，如果有错误信息或者没有输出json，我会按照数量扣你的工资
        """
        
        # 调用GPT-4o API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一个专业的股票分析师，擅长从图片中精准的提取股票交易信息。并以JSON格式输出结果。"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            max_tokens=5000
        )
        
        # 解析返回的JSON
        result = response.choices[0].message.content.strip()
        
        # 尝试解析并验证JSON格式
        try:
            stocks_data = json.loads(result)
            print(f"成功识别出{len(stocks_data)}只股票信息")
            
            # 保存到JSON文件
            with open("stock_info.json", "w", encoding="utf-8") as f:
                json.dump(stocks_data, f, ensure_ascii=False, indent=2)
            
            print("股票信息已保存到stock_info.json文件")
            return stocks_data
        except json.JSONDecodeError:
            print("API返回的数据不是有效的JSON格式:")
            print(result)
            return None
            
    except Exception as e:
        print(f"分析图片时发生错误: {e}")
        return None

def export_stock_data():
    """导出股票数据到Excel文件"""
    try:
        # 移动鼠标到屏幕中间
        screen_width, screen_height = pyautogui.size()
        pyautogui.moveTo(screen_width // 2, screen_height // 2)
        time.sleep(1)
        
        # 点击右键
        pyautogui.click(button='right')
        time.sleep(1)
        
        # 查找并点击"数据导出"选项
        # 使用剪贴板输入中文
        original_clipboard = pyperclip.paste()
        pyperclip.copy("数据导出")
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(2)
        
        # 选择导出所有数据
        pyperclip.copy("所有数据")
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(2)
        
        # 设置保存路径
        save_path = f"materials/stock_info_{datetime.now().strftime('%Y%m%d')}.xlsx"
        # 确保目录存在
        os.makedirs("materials", exist_ok=True)
        
        # 输入保存路径
        pyperclip.copy(save_path)
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
        
        # 点击下一页两次
        for _ in range(2):
            pyperclip.copy("下一页")
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(2)
        
        # 点击完成
        pyperclip.copy("完成")
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
        pyautogui.press('enter')
        
        # 还原剪贴板内容
        pyperclip.copy(original_clipboard)
        
        print(f"数据已成功导出到: {save_path}")
        return True
    except Exception as e:
        print(f"导出数据时出错: {e}")
        return False

def main():
    # 1. 打开同花顺应用
    if not open_tonghuashun_by_search():
        print("无法打开同花顺应用")
        return
    
    # 2. 等待应用完全加载
    print("等待同花顺应用加载完成...")
    time.sleep(5)
    
    try:
        # 3. 截取屏幕
        os.makedirs("img", exist_ok=True)
        screenshot_path = capture_screen("img/tonghuashun_search_51.png", window_title="同花顺")
        print(f"已完成截图: {screenshot_path}")
        
        # 4. 导出数据到Excel
        print("开始导出数据...")
        if export_stock_data():
            print("数据导出成功！")
        else:
            print("数据导出失败！")
            
    except Exception as e:
        print(f"执行过程中出错: {e}")

if __name__ == "__main__":
    main()
