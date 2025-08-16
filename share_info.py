import akshare as ak
import pandas as pd
import datetime


date_str = datetime.datetime.now().strftime("%Y%m%d")
local_file = f"D:/pythonProject/DailyKnows/materials/share_id_{date_str}.xlsx"

# 股票代码和公司名称映射
stock_names = {
    "600104": "上汽集团",
    "002594": "比亚迪",
    "00175": "吉利汽车",
    "601633": "长城汽车",
    "000625": "长安汽车",
    "601127": "赛力斯",
    "601238": "广汽集团",
    "01958": "北京汽车",
    "600418": "江淮汽车",
    "000800": "一汽解放",
    "600006": "东风股份",
    "000001": "上证指数",
    "399001": "深证成指",
    "02015": "理想汽车-W",
    "09866": "蔚来-SW",
    "09868": "小鹏汽车-W",
    "09863": "零跑汽车",
    "600741": "华域汽车",
    "600742": "富维股份",
    "300750": "宁德时代",
    "000338": "潍柴动力",
    "600699": "均胜电子",
    "002048": "宁波华翔",
    "601689": "拓普集团",
    "002074": "国轩高科",
    "000887": "中鼎股份",
    "002050": "三花智控"
}

# 根据当前时间确定日期
now = datetime.datetime.now()
if now.hour < 12:
    # 中午12点之前，取昨日日期
    aredate = (now - datetime.timedelta(days=1)).strftime("%Y%m%d")
else:
    # 中午12点之后，取当日日期
    aredate = now.strftime("%Y%m%d")

print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"使用日期: {aredate}")


df = pd.DataFrame()

for stock_code, company_name in stock_names.items():
    if len(stock_code) == 5:
        # 港股代码，使用 stock_hk_hist
        stock_hist_df = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=aredate, end_date=aredate, adjust="")
        stock_hist_df["股票代码"] = stock_code
        stock_hist_df["单位"] = "港元"
   
    elif stock_code == "000001":
        stock_hist_df = ak.index_zh_a_hist(symbol=stock_code, period="daily", start_date=aredate, end_date=aredate)
        stock_hist_df["股票代码"] = stock_code
        stock_hist_df["单位"] = "元"

    elif len(stock_code) == 6:
        # A股代码，使用 stock_zh_a_hist
        stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=aredate, end_date=aredate, adjust="")
        stock_hist_df["股票代码"] = stock_code
        stock_hist_df["单位"] = "元"
    else:
        print(f"未知的股票代码格式: {stock_code}")
        continue
    
    # 添加公司名称
    stock_hist_df["公司名称"] = company_name
    
    df = pd.concat([df, stock_hist_df])

#只要日期，股票代码，公司名称，收盘，单位，涨跌幅，涨跌额字段
df = df[["日期", "股票代码", "公司名称", "收盘", "单位", "涨跌幅", "涨跌额"]]

# 将涨跌幅转换为小数格式（为Excel百分数格式做准备）
df["涨跌幅"] = df["涨跌幅"] / 100

# 收盘价保留2位小数
df["收盘"] = df["收盘"].round(2)

print(df)	


#保存至local_file，并设置格式
with pd.ExcelWriter(local_file, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    
    # 找到涨跌幅列的索引
    col_index_change = df.columns.get_loc("涨跌幅") + 1  # Excel列索引从1开始
    col_letter_change = chr(64 + col_index_change)  # 转换为Excel列字母
    
    # 找到收盘价列的索引
    col_index_close = df.columns.get_loc("收盘") + 1
    col_letter_close = chr(64 + col_index_close)
    
    # 设置涨跌幅列为百分数格式
    for row in range(2, len(df) + 2):  # 从第2行开始（跳过标题行）
        # 涨跌幅列设置为百分数格式
        cell_change = worksheet[f'{col_letter_change}{row}']
        cell_change.number_format = '0.00%'
        
        # 收盘价列设置为保留2位小数格式
        cell_close = worksheet[f'{col_letter_close}{row}']
        cell_close.number_format = '0.00'
