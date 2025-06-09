import os
import time
from DrissionPage import Chromium, ChromiumOptions
from seatable_api import Base
from datetime import date


def fetch_stock_data(url):
    # 配置浏览器选项 - 添加无头环境必要参数
    co = ChromiumOptions().headless()  # 无头模式
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')

    browser = Chromium(co)
    page = browser.latest_tab
    page.get(url)

    # 添加等待，确保页面加载完成
    time.sleep(15)  # 等待5秒，确保数据加载

    trs = page.eles('css:#ggmx > div.ggmxcont > div.ggmx.clearfix > div.leftcol.fl > div > div > table > tbody > tr')
    return browser, trs  # 返回浏览器对象和爬取的数据


def parse_stock_data(trs):
    data_list = []
    current_date = date.today()

    for tr in trs:
        text = tr.text.strip()
        parts = [p.strip() for p in text.split()]

        period = None
        if parts[0] == '3日':
            period = parts[0]
            parts = parts[1:]

        code, name, price, change, volume, net_volume = parts[:6]

        def convert_amount(amt_str):
            if '万' in amt_str:
                return str(int(float(amt_str.replace('万', '').replace(',', '')) * 10000))
            elif '亿' in amt_str:
                return str(int(float(amt_str.replace('亿', '').replace(',', '')) * 100000000))
            return amt_str.replace(',', '')

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

    for item in data_list:
        row_data = {key: item[key] for key in [
            'code', 'name', 'price', 'change_percent',
            'sales_amount_text', 'sales_amount',
            'net_volume_text', 'net_volume', 'date'
        ]}
        base.append_row(table_name, row_data)


if __name__ == "__main__":
    print("🚀 开始执行爬虫")
    
    URL = "https://data.10jqka.com.cn/market/longhu/"
    SERVER_URL = "https://cloud.seatable.cn/"
    # 从环境变量获取API_TOKEN
    API_TOKEN = os.getenv('SEATABLE_API_TOKEN', '')
    TABLE_NAME = "Table1"  # 指定位置

    # 如果API_TOKEN不存在，则退出
    if not API_TOKEN:
        print("错误: SEATABLE_API_TOKEN 环境变量未设置")
        exit(1)

    browser, stock_trs = fetch_stock_data(URL)
    parsed_data = parse_stock_data(stock_trs)
    upload_to_seatable(parsed_data, SERVER_URL, API_TOKEN, TABLE_NAME)
    browser.quit()  # 关闭浏览器
    print("👋 程序执行完毕")
