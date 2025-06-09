import os
import time
from DrissionPage import Chromium, ChromiumOptions
from seatable_api import Base
from datetime import date


# def fetch_stock_data(url):
#     # 配置浏览器选项 - 添加无头环境必要参数
#     co = ChromiumOptions().headless()  # 无头模式
#     co.set_argument('--no-sandbox')
#     co.set_argument('--disable-dev-shm-usage')
#
#     browser = Chromium(co)
#     page = browser.latest_tab
#     page.get(url)
#
#     # 添加等待，确保页面加载完成
#     time.sleep(15)  # 等待5秒，确保数据加载
#
#     trs = page.eles('css:#ggmx > div.ggmxcont > div.ggmx.clearfix > div.leftcol.fl > div > div > table > tbody > tr')
#     if not trs:
#         print('无数据')
#
#     return browser, trs  # 返回浏览器对象和爬取的数据


def fetch_stock_data(url):
    # 配置浏览器选项
    co = ChromiumOptions().headless()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-software-rasterizer')
    co.set_argument('--disable-extensions')
    co.set_argument('--disable-infobars')
    co.set_argument('--disable-notifications')
    co.set_argument('--disable-popup-blocking')
    co.set_argument('--remote-debugging-port=9222')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    co.set_argument('--window-size=1920,1080')

    # 创建浏览器实例
    browser = Chromium(co)
    page = browser.latest_tab

    # 修正参数名 loader
    page.set.timeouts(loader=60)  # 60秒超时

    try:
        print(f"🌐 正在访问: {url}")
        page.get(url)
        print("✅ 页面加载成功")
    except Exception as e:
        print(f"❌ 页面加载失败: {e}")
        return browser, []

    # 智能等待数据加载
    print("⏳ 等待数据加载...")
    try:
        # 使用更可靠的等待方式
        page.wait.load_start()
        page.wait.doc_loaded()

        # 等待特定元素出现
        selector = '#ggmx > div.ggmxcont > div.ggmx.clearfix > div.leftcol.fl > div > div > table > tbody > tr'
        if not page.wait.ele_displayed(selector, timeout=30):
            print("❌ 数据表格未显示")
            # 保存页面用于调试
            page_html = page.html
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page_html)
            print("已保存页面到 debug_page.html")
            return browser, []
    except Exception as e:
        print(f"❌ 等待数据超时: {e}")
        return browser, []

    # 获取数据行
    trs = page.eles(selector)
    print(f"🔍 找到 {len(trs)} 行数据")

    if not trs:
        print("⚠️ 未获取到数据，尝试滚动页面...")
        page.scroll.to_bottom()
        time.sleep(2)
        trs = page.eles(selector)
        print(f"滚动后找到 {len(trs)} 行数据")

    if not trs:
        print("❌ 仍然未获取到数据，保存页面用于分析")
        page_html = page.html
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(page_html)
        print("已保存页面到 debug_page.html")

    return browser, trs

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
