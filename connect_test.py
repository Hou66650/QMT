import asyncio

import aiohttp
import numpy as np
import requests
import json
import time
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from playsound import playsound
import webbrowser

from tornado import concurrent

# 取消panda科学计数法,保留4位有效小数位.
pd.set_option('float_format', lambda x: '%.3f' % x)
# 设置中文对齐,数值等宽对齐.
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 500)

# Token accessToken 及权限校验机制
getAccessTokenUrl = 'https://quantapi.51ifind.com/api/v1/get_access_token'
refreshtoken = 'eyJzaWduX3RpbWUiOiIyMDI1LTAyLTI0IDE1OjE2OjMzIn0=.eyJ1aWQiOiI3NzAwMTQ4ODYiLCJ1c2VyIjp7ImFjY291bnQiOiJ6enh4djAwMiIsImF1dGhVc2VySW5mbyI6e30sImNvZGVDU0kiOltdLCJjb2RlWnpBdXRoIjpbXSwiaGFzQUlQcmVkaWN0IjpmYWxzZSwiaGFzQUlUYWxrIjpmYWxzZSwiaGFzQ0lDQyI6ZmFsc2UsImhhc0NTSSI6ZmFsc2UsImhhc0V2ZW50RHJpdmUiOmZhbHNlLCJoYXNGVFNFIjpmYWxzZSwiaGFzRmFzdCI6ZmFsc2UsImhhc0Z1bmRWYWx1YXRpb24iOmZhbHNlLCJoYXNISyI6dHJ1ZSwiaGFzTE1FIjpmYWxzZSwiaGFzTGV2ZWwyIjpmYWxzZSwiaGFzUmVhbENNRSI6ZmFsc2UsImhhc1RyYW5zZmVyIjpmYWxzZSwiaGFzVVMiOmZhbHNlLCJoYXNVU0FJbmRleCI6ZmFsc2UsImhhc1VTREVCVCI6ZmFsc2UsIm1hcmtldEF1dGgiOnsiRENFIjpmYWxzZX0sIm1hcmtldENvZGUiOiIxNjszMjsxNDQ7MTc2OzExMjs4ODs0ODsxMjg7MTY4LTE7MTg0OzIwMDsyMTY7MTA0OzEyMDsxMzY7MjMyOzU2Ozk2OzE2MDs2NDsiLCJtYXhPbkxpbmUiOjEsIm5vRGlzayI6ZmFsc2UsInByb2R1Y3RUeXBlIjoiU1VQRVJDT01NQU5EUFJPRFVDVCIsInJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNS0wMy0yNiAxNDoxOTozOCIsInNlc3NzaW9uIjoiZTUwOTMxODdkNTc1NjQwN2M4ZWM0ZjIxMGViNzlhMzAiLCJzaWRJbmZvIjp7fSwidHJhbnNBdXRoIjpmYWxzZSwidWlkIjoiNzcwMDE0ODg2IiwidXNlclR5cGUiOiJGUkVFSUFMIiwid2lmaW5kTGltaXRNYXAiOnt9fX0=.B966B4FB008B84D2C6B9DE0FF1F326DF582E11D4E9CD77E6071C980EBDADC9D5'
getAccessTokenHeader = {"Content-Type": "application/json", "refresh_token": refreshtoken}
getAccessTokenResponse = requests.post(url=getAccessTokenUrl, headers=getAccessTokenHeader)
accessToken = json.loads(getAccessTokenResponse.content)['data']['access_token']
print(accessToken)
thsHeaders = {"Content-Type": "application/json", "access_token": accessToken}


# 高频序列：获取分钟数据
def high_frequency():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/high_frequency'
    thsPara = {"codes":
                   "000001.SZ",
               "indicators":
                   "open,high,low,close,volume,amount,changeRatio",
               "starttime":
                   "2025-02-27 09:15:00",
               "endtime":
                   "2025-02-27 10:15:00"}
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


def open_urls_in_new_windows(stock_codes):
    """
    在新的浏览器窗口中依次打开指定股票代码列表对应的东方财富行情页面
    :param stock_codes: 股票代码列表，例如 ['SH600000', 'SZ000001']
    """
    base_url = "https://quote.eastmoney.com/concept/"
    for stock_code in stock_codes:
        url = base_url + stock_code + ".html"
        try:
            webbrowser.open_new(url)
            print(f"成功在新窗口中打开网址: {url}")
        except Exception as e:
            print(f"打开网址 {url} 时出现错误: {e}")


# 基础数据：获取证券基本信息、财务指标、盈利预测、日频行情等数据
def basic_data():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/basic_data_service'
    thsPara = {"codes":
                   "300033.SZ,600000.SH",
               "indipara":
                   [
                       {
                           "indicator":
                               "ths_regular_report_actual_dd_stock",
                           "indiparams":
                               ["104"]
                       },
                       {
                           "indicator":
                               "ths_total_shares_stock",
                           "indiparams":
                               ["20220705"]
                       }
                   ]
               }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)
    return thsResponse.content


# 实时行情：循环获取最新行情数据
def real_time(codes, indicators):
    while True:
        thsUrl = 'https://quantapi.51ifind.com/api/v1/real_time_quotation'
        thsPara = {"codes": codes, "indicators": indicators}
        thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
        data = json.loads(thsResponse.content)
        result = pd.json_normalize(data['tables'])
        result = result.drop(columns=['pricetype'])
        result = result.apply(lambda x: x.explode().astype(str).groupby(level=0).agg(", ".join))
        print(result['table.latest'])
        time.sleep(0.2)
        pass


def fetch_data(thsPara):
    try:
        thsUrl = 'https://quantapi.51ifind.com/api/v1/real_time_quotation'
        thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
        thsResponse.raise_for_status()
        data = json.loads(thsResponse.content)
        result = pd.json_normalize(data['tables'])
        if 'pricetype' in result.columns:
            result = result.drop(columns=['pricetype'])
        result = result.apply(lambda x: x.explode().astype(str).groupby(level=0).agg(", ".join))
        if 'table.latest' in result.columns:
            return result['table.latest'].tolist()
        return []
    except requests.RequestException as e:
        print(f"网络请求出错: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON 解析出错: {e}")
    except KeyError as e:
        print(f"数据中缺少必要的键: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")
    return []


def real_time_2(codes, indicators):
    all_results = []
    while True:
        # 构建请求参数列表
        thsParas = [{"codes": [code], "indicators": indicators} for code in codes]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 并行执行请求
            results = list(executor.map(fetch_data, thsParas))
        # 确保结果顺序和输入顺序一致
        combined_results = [res for sublist in results for res in sublist]
        all_results.append(combined_results)
        print(combined_results)
        time.sleep(0.2)


# json结构体转dataframe
def Trans2df(data):
    df = pd.json_normalize(data['tables'])
    df2 = df.set_index(['thscode'])

    unnested_lst = []
    for col in df2.columns:
        unnested_lst.append(df2[col].apply(pd.Series).stack())

    result = pd.concat(unnested_lst, axis=1, keys=df2.columns)
    # result = result.reset_index(drop=True)
    # 设置二级索引
    result = result.reset_index()
    result = result.set_index(['thscode', 'time'])
    # 格式化,行转列
    result = result.drop(columns=['level_1'])
    result = result.reset_index()
    return (result)


# 智能选股
def WCQuery():
    thsUrl = 'https://quantapi.51ifind.com/api/v1/smart_stock_picking'
    thsPara = {
        "searchstring": "涨跌幅",
        "searchtype": "stock"
    }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    print(thsResponse.content)


# 日期序列：与基础数据指标相同，可以同时获取多日数据
def date_serial(today_data):
    # 可算出收盘价
    thsUrl = 'https://quantapi.51ifind.com/api/v1/date_sequence'
    startdate = str(int(today_data) - 19)
    thsPara = {"codes":
                   "000001.SZ,600000.SH",
               "startdate":
                   startdate,
               "enddate":
                   str(today_data),
               "functionpara":
                   {"Fill": "Blank"},
               "indipara":
                   [
                       {
                           "indicator":
                               "ths_close_price_stock",
                           "indiparams":
                               ["", "100", ""]
                       },
                       {"indicator":
                            "ths_total_shares_stock",
                        "indiparams":
                            [""]
                        }
                   ]
               }
    thsResponse = requests.post(url=thsUrl, json=thsPara, headers=thsHeaders)
    data = json.loads(thsResponse.content)
    main_data = data['tables']
    print(main_data)
    result = Trans2df(data)
    print(result)
    return main_data


# 弹窗函数
def show_confirm_popup(message, sound_path):
    try:
        # 播放提示音
        playsound(sound_path)
    except Exception as e:
        print(f"播放提示音时出错: {e}")
    root = tk.Tk()
    root.withdraw()
    # 使用 askokcancel 方法显示带有确认和取消按钮的弹窗
    result = messagebox.askokcancel("确认提示", message)
    if result:
        print("用户点击了确认按钮")
    else:
        print("用户点击了取消按钮")
    root.destroy()


def sell_logic(main_dates, stock_symbols):
    """
    卖出逻辑
    :param stock_price:
    :param main_date:为多个dict，存有多类数据
    :return:
    """
    close_prices = []
    new_close_prices = []
    smas = []
    for stock_symbol in stock_symbols:
        # 对齐操作
        for main_data in main_dates:
            if main_data['thscode'] == stock_symbol:
                close_prices.append(main_data['table']['ths_close_price_stock'])
            else:
                pass
    new_list = [[12.11], [13.14]]
    # 加入新的价格的逻辑
    for close_price, new_list_ in zip(close_prices, new_list):
        close_price.extend(new_list_)
        new_close_prices.append(close_price)
    close_prices = new_close_prices
    prices = np.array(close_prices)
    # 添加判断条件
    open_urls_in_new_windows(stock_codes=['SH600000', 'SZ000001'])
    show_confirm_popup('是否确认买入？', r'D:\A-同花顺\代码\sound\io.wav')

    # 定义滚动窗口大小，例如计算 3 日的统计数据
    window_size = 15
    # 布林带计算中的常数 k，通常取 2
    k = 2

    # 获取数据的行数（代表数据组数）和列数（代表每组数据的时间点数）
    num_sequences, num_time_points = prices.shape

    # 初始化存储 SMA、SD 和下轨线的数组，初始值全为 NaN
    sma = np.full((num_sequences, num_time_points), np.nan)
    sd = np.full((num_sequences, num_time_points), np.nan)
    lower_band = np.full((num_sequences, num_time_points), np.nan)

    # 遍历每一组数据
    for seq_idx in range(num_sequences):
        # 从第 window_size - 1 个位置开始遍历，因为前面数据点不足以构成完整窗口
        for time_idx in range(window_size - 1, num_time_points):
            # 提取当前组在当前窗口内的数据
            window = prices[seq_idx, time_idx - window_size + 1:time_idx + 1]
            # 计算当前窗口内数据的简单移动平均线
            sma[seq_idx, time_idx] = np.mean(window)
            # 计算当前窗口内数据的标准差
            sd[seq_idx, time_idx] = np.std(window)
            # 根据 SMA 和 SD 计算布林带的下轨线
            lower_band[seq_idx, time_idx] = sma[seq_idx, time_idx] - k * sd[seq_idx, time_idx]

    print("简单移动平均线 (SMA):")
    print(sma)
    print("滚动标准差 (SD):")
    print(sd)
    print("布林带的下轨线:")
    print(lower_band)


# 模拟交易函数
def simulate_trade(codes, buy_threshold, sell_threshold):
    position = 0  # 持仓数量，0 表示未持仓
    while True:
        try:
            # 获取实时行情数据
            data = real_time(codes, "latest")
            latest_price_str = data['latest'].values[0]
            try:
                latest_price = float(latest_price_str)
            except ValueError:
                print(f"无法将 {latest_price_str} 转换为浮点数，跳过此次操作")
                time.sleep(10)
                continue

            if position == 0:
                # 未持仓，判断是否买入
                if latest_price < buy_threshold:
                    print(f"当前价格 {latest_price} 低于买入阈值 {buy_threshold}，买入 {codes}")
                    position = 1  # 假设买入 1 股
            else:
                # 持仓，判断是否卖出
                if latest_price > sell_threshold:
                    print(f"当前价格 {latest_price} 高于卖出阈值 {sell_threshold}，卖出 {codes}")
                    position = 0  # 卖出持仓

            # 每 10 秒获取一次数据
            time.sleep(10)
        except Exception as e:
            print(f"发生错误: {e}")
            time.sleep(10)


if __name__ == '__main__':
    # codes = "300033.SZ"
    # buy_threshold = 20  # 买入阈值
    # sell_threshold = 25  # 卖出阈值
    # simulate_trade(codes, buy_threshold, sell_threshold)
    # high_frequency()

    # date_serial(20250227)
    # stock_symbols = ['000001.SZ', '600000.SH']
    # sell_logic(date_serial(20250227), stock_symbols)
    # real_time('600000.sh', 'latest')
    codes = ["600000.sh", "600001.sh"]  # 示例股票代码列表
    indicators = 'latest'  # 示例指标列表
    real_time(codes, indicators)
