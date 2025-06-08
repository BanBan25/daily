from DrissionPage import Chromium, ChromiumOptions
from seatable_api import Base
from datetime import date
import os

def fetch_stock_data(url):
    co = ChromiumOptions().headless()  # 无头模式
    browser = Chromium(co)
    page = browser.latest_tab
    page.get(url)
    page.wait(3)  # 增加等待时间确保加载完成
    
    # 使用更健壮的选择器
    trs = page.eles('css:#ggmx > div.ggmxcont > div.ggmx.clearfix > div.leftcol.fl > div > div > table > tbody > tr')
    return browser, trs

def parse_stock_data(trs):
    data_list = []
    current_date = date.today()

    for tr in trs:
        text = tr.text.strip()
        parts = [p.strip() for p in text.split() if p.strip()]
        
        # 跳过表头行
        if '代码' in text or len(parts) < 6:
            continue
            
        # 处理"3日"特殊标记
        period = None
        if parts[0] == '3日':
            period = parts[0]
            parts = parts[1:]
        
        # 数据完整性检查
        if len(parts) < 6:
            continue
            
        code, name, price, change, volume, net_volume = parts[:6]

        # 金额统一转换
        def convert_amount(amt_str):
            if '万' in amt_str:
                return str(int(float(amt_str.replace('万', '').replace(',', '')) * 10000))
            elif '亿' in amt_str:
                return str(int(float(amt_str.replace('亿', '').replace(',', '')) * 100000000))
            return amt_str.replace(',', '')
        
        # 构造数据字典
        stock_data = {
            'period': period,
            'code': code,
            'name': name,
            'price': price,
            'change_percent': change,
            'sales_amount_text': volume,
            'sales_amount': convert_amount(volume),
            'net_volume_text': net_volume,
            'net_volume': convert_amount(net_volume),
            'date': str(current_date)
        }
        data_list.append(stock_data)
        
    return data_list

def upload_to_seatable(data_list, server_url, api_token, table_name):
    base = Base(api_token, server_url)
    base.auth()
    
    # 添加去重逻辑（避免重复记录）
    existing_codes = set()
    query = f"select code from `{table_name}` where date='{str(date.today())}'"
    for row in base.query(query):
        existing_codes.add(row.get('code'))
    
    # 仅上传新数据
    new_rows = 0
    for item in data_list:
        if item['code'] in existing_codes:
            continue
            
        row_data = {key: item[key] for key in [
            'code', 'name', 'price', 'change_percent',
            'sales_amount_text', 'sales_amount',
            'net_volume_text', 'net_volume', 'date'
        ]}
        base.append_row(table_name, row_data)
        new_rows += 1
        
    print(f"成功上传 {new_rows}/{len(data_list)} 条新记录")

if __name__ == "__main__":
    # 从环境变量获取敏感信息
    SERVER_URL = os.getenv('SEATABLE_SERVER_URL', 'https://cloud.seatable.cn/')
    API_TOKEN = os.getenv('SEATABLE_API_TOKEN')
    TABLE_NAME = os.getenv('SEATABLE_TABLE', 'Table1')
    URL = "https://data.10jqka.com.cn/market/longhu/"
    
    if not API_TOKEN:
        raise ValueError("SEATABLE_API_TOKEN 环境变量未设置")

    try:
        browser, stock_trs = fetch_stock_data(URL)
        print(f"获取到 {len(stock_trs)} 行数据")
        
        if not stock_trs:
            print("未获取到数据，请检查网页结构是否变化")
        else:
            parsed_data = parse_stock_data(stock_trs)
            print(f"解析出 {len(parsed_data)} 条有效数据")
            upload_to_seatable(parsed_data, SERVER_URL, API_TOKEN, TABLE_NAME)
            
    except Exception as e:
        print(f"执行出错: {str(e)}")
        raise
    finally:
        if 'browser' in locals():
            browser.quit()
        print("爬取任务完成")
