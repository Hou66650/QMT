import requests
from bs4 import BeautifulSoup
import csv

# 假设网页的 URL，这里你需要替换为实际的网页 URL
url = 'http://www.txsec.com/inc1/gpdm.asp'

try:
    # 发送请求获取网页内容
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    response.encoding = 'gb2312'  # 根据网页的编码设置响应的编码

    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # 找到表格
    table = soup.find('table')

    # 初始化一个列表来存储股票数据
    stock_data = []

    # 遍历表格的每一行
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 2:
            # 提取股票代码和名称
            for i in range(0, len(cells), 2):
                code = cells[i].text.strip()
                name = cells[i + 1].text.strip()
                stock_data.append([code, name])

    # 保存为 CSV 文件
    with open('stock_data.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # 写入表头
        writer.writerow(['股票代码', '股票名称'])
        # 写入股票数据
        writer.writerows(stock_data)

    print('数据已成功保存为 stock_data.csv 文件。')

except requests.RequestException as e:
    print(f'请求网页时出错: {e}')
except Exception as e:
    print(f'发生错误: {e}')