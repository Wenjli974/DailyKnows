#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主程序 - 自动执行新闻采集、摘要生成和简报制作的完整流程
"""

import os
import sys
import subprocess
from datetime import datetime
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("daily_news_process.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DailyKnows")

def run_script(script_name, description):
    """运行指定的脚本并返回执行结果"""
    start_time = time.time()
    logger.info(f"开始执行{description}...")
    
    try:
        result = subprocess.run(
            ["python", script_name], 
            check=True, 
            text=True, 
            capture_output=True
        )
        
        execution_time = time.time() - start_time
        logger.info(f"{description}执行成功，耗时 {execution_time:.2f} 秒")
        logger.debug(f"输出: {result.stdout}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{description}执行失败: {e}")
        logger.error(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"{description}执行时出现未知错误: {str(e)}")
        return False

def main():
    """主函数，按顺序执行各个模块"""
    logger.info("============= 开始每日新闻处理流程 =============")
    
    date_str = datetime.now().strftime("%Y%m%d")
    logger.info(f"当前处理日期: {date_str}")
    
    # 1. 执行第一财经新闻爬虫
    if not run_script("news_crawler_playwright_DYCJ.py", "第一财经新闻爬虫"):
        logger.warning("第一财经新闻爬虫执行失败，但流程将继续")
    
    # 2. 执行人民日报新闻爬虫
    if not run_script("news_crawler_playwright_RMRB.py", "人民日报新闻爬虫"):
        logger.warning("人民日报新闻爬虫执行失败，但流程将继续")
    
    # 2. 执行新华网新闻爬虫
    if not run_script("news_crawler_playwright_XinHua.py", "新华网新闻爬虫"):
        logger.warning("新华网新闻爬虫执行失败，但流程将继续")
    
    # 暂停一下，确保文件已正确写入
    time.sleep(2)
    
    # 4. 执行新闻摘要生成
    if not run_script("news_summary_llm.py", "新闻摘要生成"):
        logger.error("新闻摘要生成失败，流程无法继续")
        return
    
    # 暂停一下，确保文件已正确写入
    time.sleep(2)
    
    # 5. 执行新闻简报生成
    if not run_script("create_news_brief.py", "新闻简报文档生成"):
        logger.error("新闻简报文档生成失败")
        return
    
    logger.info("============= 每日新闻处理流程完成 =============")
    
    # 获取当前日期的中文格式
    date_str_cn = datetime.now().strftime("%Y年%m月%d日")
    output_file = f"{date_str_cn} 新闻简报.docx"
    
    if os.path.exists(output_file):
        logger.info(f"生成的新闻简报文件: {output_file}")
        logger.info("处理完成，请查看新闻简报文档")
    else:
        logger.warning(f"未找到期望的输出文件: {output_file}")

if __name__ == "__main__":
    main() 