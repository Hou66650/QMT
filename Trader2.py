import logging
import os
import queue
import copy
import subprocess
from datetime import datetime

from bs4 import BeautifulSoup
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    import pyi_splash

    pyi_splash.close()
except ImportError:
    pass
from pydub import AudioSegment
import simpleaudio as sa
import json
import webbrowser
import easytrader
import time
import tkinter as tk
import numpy as np
import pandas as pd
import requests
import threading
import itertools
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import markdown


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("real_time.log"),
        logging.StreamHandler()
    ]
)


class SimilarityProcessor:
    def __init__(self, target_count, reference_array):
        # 存储输入的子列表
        self.input_lists = []
        self.state = None
        # 设定要从一维列表中选取的元素个数
        self.target_count = target_count
        # 存储参考数组
        self.reference_array = reference_array
        self.selected_elements = None
        self.threshold = 0

    def add_list(self, new_list, times):
        # 将新列表添加到输入列表中
        self.input_lists.append(new_list)
        if len(self.input_lists) == times:
            self.state = True
            # 当输入列表达到 3 个时，进行后续处理
            self.process_lists()
        return None

    def process_lists(self):
        # 将三个列表合并成一维列表
        flat_list = list(itertools.chain(*self.input_lists))
        print('flat_list', flat_list)
        self.input_lists.clear()
        # self.state = False
        # 找出相似度最低的 target_count 个元素
        self.selected_elements = self.select_dissimilar_elements_p(flat_list)

    def select_dissimilar_elements(self, flat_list):
        # 生成所有可能的元素组合，并过滤掉有重复元素的组合
        all_combinations = [comb for comb in itertools.combinations(flat_list, self.target_count) if
                            len(set(comb)) == len(comb)]
        if len(all_combinations) == 0:
            print(all_combinations)
        best_combination = None
        max_total_difference = float('-inf')

        for combination in all_combinations:
            # 计算当前组合与参考数组的总差值
            total_difference = self.calculate_total_difference(combination, self.reference_array)
            if total_difference > max_total_difference:
                max_total_difference = total_difference
                best_combination = combination
                if best_combination is None:
                    print('asjdjl')

                else:
                    print('00', best_combination)

        return list(best_combination)

    def select_dissimilar_elements_p(self, flat_list):
        all_combinations = [comb for comb in itertools.combinations(flat_list, self.target_count) if
                            len(set(comb)) == len(comb)]
        if len(all_combinations) == 0:
            print(all_combinations)
            return []

        for combination in all_combinations:
            total_difference = self.calculate_total_difference_p(combination, self.reference_array)
            if total_difference >= self.threshold:
                print('找到接近的组合:', combination)
                return list(combination)

        best_combination = None
        max_total_difference = float('-inf')
        for combination in all_combinations:
            total_difference = self.calculate_total_difference_p(combination, self.reference_array)
            if total_difference > max_total_difference:
                max_total_difference = total_difference
                best_combination = combination

        return list(best_combination) if best_combination else []

    def calculate_total_difference(self, combination, reference_array):
        total_difference = 0
        # 对组合和参考数组进行全排列匹配，找出最大的总差值
        all_permutations = itertools.permutations(combination)
        max_difference = float('-inf')
        for permutation in all_permutations:
            current_difference = sum(abs(a - b) for a, b in zip(permutation, reference_array))
            max_difference = max(max_difference, current_difference)
        return max_difference

    def calculate_total_difference_p(self, combination, reference_array):
        return max(sum(abs(a - b) for a, b in zip(permutation, reference_array))
                   for permutation in itertools.permutations(combination))

    def compare_and_sort(self, selected_elements, reference_array):
        if len(selected_elements) != len(reference_array):
            raise ValueError("两个数组的长度必须相同")
        # 按照参考数组的顺序找到最接近的元素
        sorted_selected_elements = []
        remaining_elements = selected_elements.copy()
        for ref in reference_array:
            closest_element = min(remaining_elements, key=lambda x: abs(x - ref))
            sorted_selected_elements.append(closest_element)
            remaining_elements.remove(closest_element)
        return sorted_selected_elements


class PriceProcessor:
    def __init__(self):
        # 初始化 self.real_prices_p 和 self.real_prices_g
        self.real_prices_p = []
        self.real_prices_g = []

    def calculate_means(self, sublists):
        """
        计算每个子列表的均值，返回一个包含均值的列表
        """
        return [sum(sublist) / len(sublist) if sublist else 0 for sublist in sublists]

    def is_close(self, list1, list2, threshold=2.5):
        """
        判断两个列表的元素是否满足条件：每个元素相应相减取平方，然后相加取均值，小于阈值
        """
        if len(list1) != len(list2):
            return False
        squared_differences_sum = sum((val1 - val2) ** 2 for val1, val2 in zip(list1, list2))
        mean_squared_difference = squared_differences_sum / len(list1)
        return mean_squared_difference < threshold

    def process_sublists(self, sublists):
        """
        处理子列表，计算均值并与 self.real_prices_p 进行条件判断
        """
        means = self.calculate_means(sublists)
        self.real_prices_g = means


class TradingTimeCalculator:
    def __init__(self):
        import datetime
        # 定义早市和午市的时间范围
        self.morning_start = datetime.time(9, 30)
        self.morning_end = datetime.time(11, 30)
        self.afternoon_start = datetime.time(13, 0)
        self.afternoon_end = datetime.time(15, 0)
        # 早市和午市的时长（分钟）
        self.morning_duration = 120
        self.afternoon_duration = 120
        self.total_trading_duration = self.morning_duration + self.afternoon_duration
        self.buy_state = None

    def is_weekday(self, date):
        """判断是否为工作日"""
        return date.weekday() < 5

    def calculate_previous_time(self, input_time_str, target_minutes):
        import datetime
        # 将输入的时间字符串转换为 datetime 对象
        input_time = datetime.datetime.strptime(input_time_str, '%Y-%m-%d %H:%M:%S')
        remaining_minutes = target_minutes

        # 判断输入时间处于早市还是午市，并计算第一个时间差
        if self.morning_start <= input_time.time() <= self.morning_end:
            first_time_diff = (input_time - datetime.datetime.combine(input_time.date(),
                                                                      self.morning_start)).total_seconds() / 60
            if first_time_diff >= remaining_minutes:
                result_time = input_time - datetime.timedelta(minutes=remaining_minutes)
                return result_time.strftime('%Y-%m-%d %H:%M:%S')
            remaining_minutes -= first_time_diff
        elif self.afternoon_start <= input_time.time() <= self.afternoon_end:
            first_time_diff = (input_time - datetime.datetime.combine(input_time.date(),
                                                                      self.afternoon_start)).total_seconds() / 60
            remaining_minutes -= first_time_diff
            if remaining_minutes <= 0:
                result_time = input_time - datetime.timedelta(minutes=target_minutes)
                return result_time.strftime('%Y-%m-%d %H:%M:%S')
            remaining_minutes -= self.morning_duration
            if remaining_minutes <= 0:
                result_date = input_time.date()
                result_time = datetime.datetime.combine(result_date, self.morning_end) - datetime.timedelta(
                    minutes=-remaining_minutes)
                return result_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.buy_state = False
            raise ValueError("输入的时间不在交易时间范围内")

        # 往前推日期
        current_date = input_time.date()
        while remaining_minutes > 0:
            current_date = current_date - datetime.timedelta(days=1)
            if self.is_weekday(current_date):
                if remaining_minutes > self.total_trading_duration:
                    remaining_minutes -= self.total_trading_duration
                else:
                    if remaining_minutes <= self.afternoon_duration:
                        result_time = datetime.datetime.combine(current_date, self.afternoon_end) - datetime.timedelta(
                            minutes=remaining_minutes)
                    else:
                        remaining_in_morning = remaining_minutes - self.afternoon_duration
                        result_time = datetime.datetime.combine(current_date, self.morning_end) - datetime.timedelta(
                            minutes=remaining_in_morning)
                    return result_time.strftime('%Y-%m-%d %H:%M:%S')


class Trader:

    def __init__(self, sound_path):
        # 时间相关属性
        self.indices = None
        self.fix_value = None
        self.data_queue = queue.Queue()
        self.end_time1 = 0
        self.start_time = 0
        self.start_time_list = []
        self.limit_time = 40
        self.backtime = None
        self.formatted_time = None
        self.end_time = None
        self.new_time_str = None

        # 比率相关属性
        self.ratio = 0
        self.ratio_list = []
        self.ratio_list_all = []
        self.ratio_threshold = 0.005

        # 交易状态相关属性
        self.buy_state = None
        self.buy_state_set = []
        self.buy_state_fina = False
        self.state = None
        self.state_buy = None

        # 股票代码和价格相关属性
        self.stock_symbols = []
        self.prices = []
        self.real_prices = []
        self.real_price = None
        self.real_prices_g = None
        self.close_prices = []
        self.close_prices_15min = []
        self.close_prices_15min_new = []
        self.close_prices_15min_new_ = []
        self.sorted_selected_elements = None
        self.smas = []
        self.stock_dict = {}

        # 代码列表相关属性
        self.codes_list_confirm_exchange = None
        self.times = 1
        self.codes_list = []
        self.codes_list_confirm = []
        self.codes_just_code = []
        self.always_code_list = []
        self.ratio_list_all_json = [[] for _ in range(len(self.codes_list))]

        # 其他属性
        self.blacklist = []
        self.thsHeaders = None
        self.min_times = []
        self.amounts = []
        self.is_window_closed = False
        self.update_event = threading.Event()
        # 创建线程池
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.executor_shutdown = False  # 标志线程池是否已关闭
        # 创建一个 requests 会话
        self.session = requests.Session()

        # 交易客户端初始化
        self.user = easytrader.use('universal_client')

        # 声音路径
        self.sound_path = sound_path
        self.refreshtoken = 'eyJzaWduX3RpbWUiOiIyMDI1LTAzLTIwIDEzOjA5OjUzIn0=.eyJ1aWQiOiI3NzQyNjk5MzQiLCJ1c2VyIjp7ImFjY291bnQiOiJ5eWN6aDAwMiIsImF1dGhVc2VySW5mbyI6eyJhcGlGb3JtYWwiOiIxIn0sImNvZGVDU0kiOltdLCJjb2RlWnpBdXRoIjpbXSwiaGFzQUlQcmVkaWN0IjpmYWxzZSwiaGFzQUlUYWxrIjpmYWxzZSwiaGFzQ0lDQyI6ZmFsc2UsImhhc0NTSSI6ZmFsc2UsImhhc0V2ZW50RHJpdmUiOmZhbHNlLCJoYXNGVFNFIjpmYWxzZSwiaGFzRmFzdCI6ZmFsc2UsImhhc0Z1bmRWYWx1YXRpb24iOmZhbHNlLCJoYXNISyI6dHJ1ZSwiaGFzTE1FIjpmYWxzZSwiaGFzTGV2ZWwyIjpmYWxzZSwiaGFzUmVhbENNRSI6ZmFsc2UsImhhc1RyYW5zZmVyIjpmYWxzZSwiaGFzVVMiOmZhbHNlLCJoYXNVU0FJbmRleCI6ZmFsc2UsImhhc1VTREVCVCI6ZmFsc2UsIm1hcmtldEF1dGgiOnsiRENFIjpmYWxzZX0sIm1hcmtldENvZGUiOiIxNjszMjsxNDQ7MTc2OzExMjs4ODs0ODsxMjg7MTY4LTE7MTg0OzIwMDsyMTY7MTA0OzEyMDsxMzY7MjMyOzU2Ozk2OzE2MDs2NDsiLCJtYXhPbkxpbmUiOjEsIm5vRGlzayI6ZmFsc2UsInByb2R1Y3RUeXBlIjoiU1VQRVJDT01NQU5EUFJPRFVDVCIsInJlZnJlc2hUb2tlbkV4cGlyZWRUaW1lIjoiMjAyNS0wNC0xNyAxMTowNTowMiIsInNlc3NzaW9uIjoiZWI2M2I1MjEzYzc4YjQwN2M1NDVkZWNmYjRjMmNhZGYiLCJzaWRJbmZvIjp7fSwidHJhbnNBdXRoIjpmYWxzZSwidWlkIjoiNzc0MjY5OTM0IiwidXNlclR5cGUiOiJPRkZJQ0lBTCIsIndpZmluZExpbWl0TWFwIjp7fX19.DBC4DB6BC403847F513247A730A3144D6161667F5042BC5E675C325B56A0D279'

    def connect(self):
        print('Connecting to trader...')
        try:
            self.user.connect(r'C:\同花顺远航版\bin\happ.exe')
            print('Connected successfully')
            # 增加额外的等待时间，确保客户端完全启动
            time.sleep(5)
        except Exception as e:
            print(f'Connection failed: {e}')

    def adjust_minutes_to_15_min_interval(self, time_str):
        # 将输入的时间字符串转换为 datetime 对象
        from datetime import datetime
        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

        # 获取分钟数
        minutes = dt.minute

        # 计算分钟数除以 15 的余数
        remainder = minutes % 15

        # 用分钟数减去余数得到新的分钟数
        new_minutes = minutes - remainder

        # 创建新的 datetime 对象，将分钟数更新为新的分钟数
        new_dt = dt.replace(minute=new_minutes)

        # 将新的 datetime 对象转换为格式化的时间字符串
        self.new_time_str = new_dt.strftime('%Y-%m-%d %H:%M:%S')

    def init(self):
        # 取消 pandas 科学计数法，保留 4 位有效小数位
        pd.set_option('float_format', lambda x: '%.4f' % x)
        # 设置中文对齐，数值等宽对齐
        pd.set_option('display.unicode.ambiguous_as_wide', True)
        pd.set_option('display.unicode.east_asian_width', True)
        pd.set_option('display.max_columns', 20)
        pd.set_option('display.width', 500)

        # Token accessToken 及权限校验机制
        getAccessTokenUrl = 'https://quantapi.51ifind.com/api/v1/get_access_token'
        getAccessTokenHeader = {"Content-Type": "application/json", "refresh_token": self.refreshtoken}
        try:
            getAccessTokenResponse = requests.post(url=getAccessTokenUrl, headers=getAccessTokenHeader)
            # 检查请求是否成功
            getAccessTokenResponse.raise_for_status()
            response_data = json.loads(getAccessTokenResponse.content)
            accessToken = response_data['data']['access_token']
            print(accessToken)
            self.thsHeaders = {"Content-Type": "application/json", "access_token": accessToken}
        except requests.RequestException as e:
            print(f"请求出错: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            print(f"解析响应出错: {e}")

    def get_current_time_formatted(self):
        from datetime import datetime
        # 获取当前时间
        now = datetime.now()
        # 将当前时间按照指定格式进行格式化
        self.formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

    def open_urls_in_new_windows(self):
        """
        在新的浏览器窗口中依次打开指定股票代码列表对应的东方财富行情页面
        :param stock_codes: 股票代码列表，例如 ['SH600000', 'SZ000001']
        """
        base_url = "https://quote.eastmoney.com/concept/"
        self.codes_list_confirm_exchange = [self.convert_stock_code(code) for code in self.codes_list_confirm]
        for stock_code in self.codes_list_confirm_exchange:
            url = base_url + stock_code + ".html"
            try:
                webbrowser.open_new(url)
                print(f"成功在新窗口中打开网址: {url}")
            except Exception as e:
                print(f"打开网址 {url} 时出现错误: {e}")

    def judgement(self):
        # 检查是否出现漏写情况
        if len(self.stock_symbols) == len(self.prices) == len(self.amounts):
            print(f'您输入了{len(self.stock_symbols)}个股票代码')
            print(f'您输入了{len(self.prices)}个价格')
            print(f'您输入了{len(self.amounts)}个数量')
            pass
        else:
            print('Error！请检查您的输入')

    def endtime_get(self):
        calculator = TradingTimeCalculator()
        target_minutes = 285
        self.adjust_minutes_to_15_min_interval(self.formatted_time)
        self.end_time = calculator.calculate_previous_time(self.new_time_str, target_minutes)

    @staticmethod
    def convert_stock_code(code):
        '''
        ’000001.sz'------->'SZ0000001‘
        :param code:
        :return:
        '''
        parts = code.split('.')
        if len(parts) == 2:
            number, market = parts
            return market.upper() + number
        return code

    def state(self):
        '''
        判断状态
        :return:
        '''
        if isinstance(self.stock_symbols, list) and isinstance(self.prices, list) and isinstance(self.amounts, list):
            self.state = True
        else:
            self.state = False

    def stock_symbol_choose(self, stock_symbol, price, amount):
        '''
        股票代码选择
        :param stock_symbol: 股票代码----------list/str
        :param price:-----------list/float---->list/float
        :return:
        '''
        if isinstance(stock_symbol, list) and isinstance(price, list) and isinstance(amount, list):
            self.stock_symbols = stock_symbol
            self.prices = price
            self.amounts = amount
            # 检查
            self.judgement()
        elif isinstance(stock_symbol, int) and isinstance(price, float) and isinstance(amount, int):
            print(f'您输入了1个股票代码')
            self.stock_symbols = stock_symbol
            self.prices = price
            self.amounts = amount
            # 检查
            self.judgement()
        # 检查状态
        self.state()

    def get_info(self):
        try:
            # 修改客户端代码中的超时时间
            from easytrader.clienttrader import ClientTrader
            ClientTrader._get_left_menus_handle_timeout = 10  # 设置为 10 秒
            info = self.user.balance
            # 获取持仓
            position = self.user.position
            print(info, position)
            return info
        except Exception as e:
            print(f'Failed to get balance information: {e}')
            return None

    def str2just_num(self):
        '''
        将字符转换为只含有数字的
        :return:
        '''
        pattern = re.compile('[0-9]+')
        for code in self.codes_list_confirm:
            # 使用 pattern.search 查找字符串中的数字
            match = pattern.search(code)
            if match:
                # 如果找到匹配项，将匹配到的数字字符串添加到 codes_just_code 列表中
                self.codes_just_code.append(match.group())
            else:
                # 如果未找到匹配项，可根据需求处理，这里添加空字符串
                self.codes_just_code.append('')

    def show_confirm_popup(self):
        try:
            # 使用 pydub 和 simpleaudio 播放音频
            audio = AudioSegment.from_file(self.sound_path)
            play_obj = sa.play_buffer(
                audio.raw_data,
                num_channels=audio.channels,
                bytes_per_sample=audio.sample_width,
                sample_rate=audio.frame_rate
            )
            play_obj.wait_done()
        except Exception as e:
            print(f"播放提示音时出错: {e}")

        stock_dict = self.codes_list_confirm
        ratio_list = self.ratio_list
        message_part1 = f"满足要求{stock_dict}"
        message_part2 = f"\n{ratio_list}"

        root = tk.Tk()
        root.withdraw()

        # 获取屏幕宽度和高度
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # 增大窗口的宽度和高度
        dialog_width = 700  # 加大窗口宽度
        dialog_height = 400  # 加大窗口高度

        # 计算消息框在屏幕右下角并往左上方移动一点的坐标
        offset_x = 100  # 往左移动的距离
        offset_y = 100  # 往上移动的距离
        x = screen_width - dialog_width - offset_x
        y = screen_height - dialog_height - offset_y

        # 创建自定义弹窗
        top = tk.Toplevel(root)
        top.title("确认提示")
        top.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 设置显眼的背景颜色
        top.configure(bg="#FFFFFF")  # 橙色背景

        # 定义一个更大一点的字体
        large_font = ("Arial", 30)  # 加大字体

        # 使用 Text 组件显示消息内容
        text_widget = tk.Text(top, padx=20, pady=20, font=large_font, bg="#FFFFFF", fg="white", wrap=tk.WORD)
        text_widget.pack()

        # 插入红色的股票字典信息
        text_widget.insert(tk.END, message_part1, "red")
        # 插入其余消息内容
        text_widget.insert(tk.END, message_part2)

        # 配置红色标签
        text_widget.tag_configure("red", foreground="red")

        # 禁止用户编辑 Text 组件
        text_widget.config(state=tk.DISABLED)

        # 定义确认、取消和继续按钮的回调函数
        def on_confirm():
            print("用户点击了确认按钮")
            self.is_window_closed = True  # 设置标志位
            top.destroy()

        def on_cancel():
            print("用户点击了取消按钮")
            self.is_window_closed = True  # 设置标志位
            top.destroy()

        def on_continue():
            print("用户点击了继续按钮")
            self.buy_state_fina = False  # 将 self.buy_state_fina 设置为 False
            self.is_window_closed = True  # 设置标志位
            top.destroy()

        # 创建确认、取消和继续按钮，使用大字体
        button_frame = tk.Frame(top, bg="#FFA500")
        button_frame.pack(pady=20)
        confirm_button = tk.Button(button_frame, text="确认", command=on_confirm, font=large_font)
        confirm_button.pack(side=tk.LEFT, padx=10)
        cancel_button = tk.Button(button_frame, text="取消", command=on_cancel, font=large_font)
        cancel_button.pack(side=tk.LEFT, padx=10)
        continue_button = tk.Button(button_frame, text="继续", command=on_continue, font=large_font)
        continue_button.pack(side=tk.LEFT, padx=10)

        # 绑定 Enter 键到继续按钮的操作
        top.bind("<Return>", lambda event: on_continue())

        # 设置 5 秒后自动关闭窗口
        def auto_close_5s():
            if not self.is_window_closed:  # 检查标志位
                print("窗口因 5 秒超时自动关闭")
                self.is_window_closed = True  # 设置标志位
                self.buy_state_fina = False  # 将 self.buy_state_fina 设置为 False
                top.destroy()

        top.after(5000, auto_close_5s)

        # 等待窗口关闭
        top.wait_window()

        # 主程序在弹窗关闭后继续执行的代码可以放在这里
        if not self.buy_state_fina:
            print("主程序继续进行...")
            self.judge_temp_time()
            return

    def process_close_prices(self):
        # 遍历 self.close_prices 中的每个子序列
        for close_price in self.close_prices:
            close_price = self.remove_elements_by_indices(close_price, self.indices)
            # 每次处理一个新的 close_price 时，清空 close_prices_15min 列表
            close_prices_15min = []
            # 获取当前 close_price 子序列的最后一个元素的索引
            index = 14
            # 从最后一个元素开始，向前遍历 close_price 子序列
            while index <= 288:
                # 将当前索引对应的元素添加到 close_prices_15min 列表中
                close_prices_15min.append(close_price[index])
                # 每次向前移动 15 个位置
                index += 15
            # 将收集到的 close_prices_15min 列表添加到 self.close_prices_15min 中
            self.close_prices_15min.append(close_prices_15min)

    def ping_url(self, url):
        '''
        根据url获取其ping值
        :param url:
        :return: ping
        '''
        try:
            # 根据不同操作系统选择合适的命令
            if os.name == 'nt':
                # Windows 系统
                command = ['ping', '-n', '4', url]
            else:
                # Linux 和 macOS 系统
                command = ['ping', '-c', '4', url]
            result = subprocess.run(command, capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"发生错误: {e}")

    def find_930_indices(self, event_list):
        target_time = datetime.strptime("09:30", "%H:%M").time()
        indices = [i for i, event in enumerate(event_list)
                   if datetime.strptime(event, "%Y-%m-%d %H:%M").time() == target_time]
        return indices

    def remove_elements_by_indices(self, data_list, index_list):
        # 使用列表推导式，保留不在索引列表中的元素
        return [data for i, data in enumerate(data_list) if i not in index_list]

    def high_frequency(self, codes_list):
        stop_event = Event()
        while not stop_event.wait(1):
            # 进行初始化
            self.init()
            self.codes_list = codes_list
            # 获取当前时间
            self.get_current_time_formatted()
            # 获取前19个十五分钟前的时间
            self.endtime_get()

            thsUrl = 'https://quantapi.51ifind.com/api/v1/high_frequency'
            # self.ping_url(thsUrl)
            # 将代码列表转换为逗号分隔的字符串
            codes_str = ','.join(codes_list)
            thsPara = {
                "codes": codes_str,
                "indicators": "open,high,low,close",
                "starttime": self.end_time,
                "endtime": self.new_time_str,
            }
            try:
                # 发送 POST 请求
                thsResponse = requests.post(url=thsUrl, json=thsPara, headers=self.thsHeaders)
                # 检查响应状态码
                thsResponse.raise_for_status()  # 如果状态码不是 200，抛出异常
                # 自动检测编码
                thsResponse.encoding = thsResponse.apparent_encoding
                # 获取响应内容
                data_str = thsResponse.text
                # 解析 JSON 数据
                data = json.loads(data_str)
                # print(data)
            except requests.exceptions.RequestException as e:
                print(f"请求发生错误: {e}")
                continue
            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {e}")
                continue
            except Exception as e:
                print(f"发生其他错误: {e}")
                continue

            # 获取多个表格数据
            # 获取每分钟的收盘价
            # 顺序为输入的列表的顺序
            self.close_prices = []
            for i in range(len(data['tables'])):
                table = data['tables'][i]['table']
                close_price = table['close']
                self.close_prices.append(close_price)

            # 获取时间-具体
            self.min_times = []
            for i in range(len(data['tables'])):
                table = data['tables'][i]
                min_time = table['time']
                self.indices = self.find_930_indices(min_time)
                self.min_times.append(min_time)

            print(self.codes_list)
            # 获取每15分钟收盘价
            self.process_close_prices()
            # 检查长度
            self.close_prices_15min_new = []
            for close_price_15min in self.close_prices_15min:
                if len(close_price_15min) > 19:
                    close_price_15min_m = close_price_15min[:19]
                else:
                    close_price_15min_m = close_price_15min
                self.close_prices_15min_new.append(close_price_15min_m)

            print(self.close_prices_15min_new)
            self.fix_value = copy.deepcopy(self.close_prices_15min_new)

            time.sleep(240)  # 暂停4分钟再获取下一次数据
            print('240秒已到，更新数据')
            self.close_prices = []
            self.min_times.clear()
            self.close_prices_15min = []
            self.close_prices_15min_new = []

        # 清除数据，更新准备

        # # 等待 self.real_prices_g 更新
        # self.update_event.wait()

    def add_real_prices_to_15min_k_lines(self):
        """
        将 real_prices_g 中的元素添加到 close_prices_15min_new 每个子列表的末尾
        """
        # 检查两个列表长度是否一致
        if len(self.real_prices_g) == len(self.close_prices_15min_new):
            # 遍历两个列表
            for num, sublist in zip(self.real_prices_g, self.close_prices_15min_new):
                # 将数字添加到子列表的末尾
                if len(sublist) != 19:
                    sublist = sublist[:19]
                    sublist.append(num)
                else:
                    sublist.append(num)
                self.close_prices_15min_new_.append(sublist)
            print('长度一致！！！', self.close_prices_15min_new_)
        else:
            print("两个列表的长度不一致，无法进行对位添加操作。")

    def fetch_real_time_data(self, code, indicators):
        thsUrl = 'https://quantapi.51ifind.com/api/v1/real_time_quotation'
        thsPara = {"codes": code, "indicators": indicators}
        try:
            # 使用会话发送请求
            thsResponse = self.session.post(url=thsUrl, json=thsPara, headers=self.thsHeaders)
            # 检查响应状态码
            thsResponse.raise_for_status()
            data = thsResponse.json()
            if 'tables' in data:
                result = pd.json_normalize(data['tables'])
                result = result.drop(columns=['pricetype'])
                result = result.apply(lambda x: x.explode().astype(str).groupby(level=0).agg(", ".join))
                return float(result['table.latest'].iloc[0])
        except (requests.RequestException, KeyError, IndexError, ValueError):
            pass
        return None

    def output_json_get(self):
        # 逐个元素赋值到对应位置的子列表中
        for i, element in enumerate(self.ratio_list_all):
            self.ratio_list_all_json[i].append(element)
            print(self.ratio_list_all_json)

    def real_time(self, codes, indicators):
        try:
            processor = PriceProcessor()
            # 复制 self.close_prices_15min_new 的初始值
            processor_m = SimilarityProcessor(target_count=len(self.codes_list),
                                              reference_array=processor.real_prices_p)
            while True:
                initial_close_prices = self.fix_value
                if initial_close_prices:
                    logging.info("开始处理初始收盘价")
                    processor.process_sublists(initial_close_prices)

                    if len(self.codes_list) <= 5:
                        self.times = 2
                    else:
                        self.times = 2
                    for i in range(self.times):
                        # self.real_prices.clear()
                        for code in codes:
                            real_price = self.fetch_real_time_data(code, indicators)
                            if real_price is not None:
                                self.real_prices.append(real_price)
                            else:
                                logging.warning(f"获取代码 {code} 的实时价格失败，返回值为 {real_price}")

                        # 检查 self.real_prices 中的元素个数是否满足要求
                        # if len(self.real_prices) == len(self.codes_list):
                        processor.real_prices_p = self.real_prices
                        if processor.real_prices_g is not None and self.real_prices:
                            processor_m.add_list(processor.real_prices_p, self.times)
                            if len(self.real_prices) >= len(self.codes_list):
                                self.real_prices.clear()

                            if processor_m.state:
                                selected_elements = processor_m.selected_elements
                                self.sorted_selected_elements = processor_m.compare_and_sort(selected_elements,
                                                                                             processor.real_prices_g)
                                logging.info(f"选择的元素: {selected_elements}")
                                logging.info(f"排序后的元素: {self.sorted_selected_elements}")
                                processor_m.state = False
                                self.real_prices.clear()

                    self.real_prices_g = self.sorted_selected_elements
                    self.update_event.set()  # 通知 high_frequency 方法数据已更新
                    logging.info("通知 high_frequency 方法数据已更新")
                    self.add_real_prices_to_15min_k_lines()  # 获取完整20位计算布林线的值
                    # 计算布林线
                    lower_band = self.calculate_bollinger_bands()
                    logging.info(f'lower_band: {lower_band}')
                    # print(lower_band)
                    # print('Real_price', self.real_prices_g)
                    # 下面是买入逻辑。。。
                    # 遍历两个列表的对应元素
                    temp = 0
                    # _______________---------------------逻辑有误----------------------------------------------
                    # extract_non_nan函数有误
                    for num1, num2 in zip(self.extract_last_elements(lower_band), self.real_prices_g):
                        # 计算 (前面的减去后面的) 除以后面的
                        if num2 != 0:
                            self.ratio = (num2 - num1) / num2
                            logging.info(f'{self.codes_list[temp]}：{num2}对应的ratio值为：{self.ratio}')
                            self.ratio_list_all.append(self.ratio)
                        else:
                            # 避免除零错误
                            self.ratio = float('inf')
                            logging.warning(f'{self.codes_list[temp]}：{num2}对应的ratio值为无穷大，避免除零错误')
                        self.state_transition()
                        # 判断是否小于 0.005
                        if self.ratio < self.ratio_threshold:
                            self.start_time = time.time()
                            self.start_time_list.append(self.start_time)

                            self.buy_state = True

                            # 根据限定时间判断是否清空黑名单
                            self.remove_blacklist()
                            # 将符合条件的股票加入confirm中
                            self.codes_list_confirm.append(self.codes_list[temp])
                            self.is_ratio_in(temp)
                            self.ratio_list.append(self.ratio)

                            # 移除黑名单中的股票代码
                            self.judge_codes('codes_list_confirm')
                            logging.info(f"买入状态: {self.buy_state}")
                            logging.info(f"ratio值: {self.ratio}, 确认的股票代码列表: {self.codes_list_confirm}")
                            if len(self.codes_list_confirm) == 0:
                                logging.info('加入黑名单')
                                self.buy_state = False
                            self.buy_state_set.append(self.buy_state)
                        temp += 1

                    self.buy_state_fina = any(self.buy_state_set)
                    if self.buy_state_fina and self.codes_list_confirm:
                        # 打开相应网址
                        # self.open_urls_in_new_windows()
                        # 打开提示框
                        self.show_confirm_popup()
                        logging.info("满足买入条件，打开提示框")
                    else:
                        logging.info("不满足买入条件")
                    time.sleep(0.3)
                    self.close_prices_15min_new_.clear()
                    self.codes_list_confirm = []
                    self.buy_state = False
                    self.buy_state_set = []
                    self.ratio_list = []
                    self.ratio_list_all = []
                else:
                    logging.info("初始收盘价为空，等待1秒")
                    time.sleep(1)
        except Exception as e:
            logging.error(f"发生异常: {e}", exc_info=True)

    def buy(self):
        '''
        以下是交易代码
        :return:
        '''
        if self.state:
            print('您想同时进行多笔交易')
            for stock_symbol, price, amount in zip(self.stock_symbols, self.prices, self.amounts):
                self.user.buy(stock_symbol, price, amount)
                print(self.user.buy(stock_symbol, price, amount))
            self.state_buy = True
        else:
            print('您选择购买一只股票')
            self.user.buy(str(self.stock_symbols), self.prices, self.amounts)
            print(self.user.buy(str(self.stock_symbols), self.prices, self.amounts))

    @staticmethod
    def extract_last_elements(arr):
        return [sub_list[-1] for sub_list in arr]

    def state_transition(self):
        self.buy_state = False

    def calculate_bollinger_bands(self, min_value=-9999, max_value=9999):
        # 定义滚动窗口大小，例如计算 20 日的统计数据
        window_size = 20
        # 布林带计算中的常数 k，通常取 2
        k = 1.99

        # 初始化存储 SMA、SD 和下轨线的列表
        all_sma = []
        all_sd = []
        all_lower_band = []

        # 遍历每一组数据
        for price_15min in self.close_prices_15min_new_:
            prices = np.array(price_15min)
            # 初始化 SMA、SD 和下轨线数组，指定数据类型为浮点数
            sma = np.full_like(prices, np.nan, dtype=np.float64)
            sd = np.full_like(prices, np.nan, dtype=np.float64)
            lower_band = np.full_like(prices, np.nan, dtype=np.float64)

            # 计算 SMA 和 SD
            for i in range(window_size - 1, len(prices)):
                window = prices[i - window_size + 1:i + 1]
                sma[i] = np.mean(window)
                sd[i] = np.std(window)
                lower_band[i] = sma[i] - k * sd[i]

            # 将计算结果添加到对应的列表中
            all_sma.append(sma)
            all_sd.append(sd)
            all_lower_band.append(lower_band)

        # 将列表转换为 numpy 数组
        sma = np.array(all_sma)
        sd = np.array(all_sd)
        lower_band = np.array(all_lower_band)

        # 把太大或太小的数据定位为 np.nan
        if min_value is not None:
            lower_band[lower_band < min_value] = np.nan
        if max_value is not None:
            lower_band[lower_band > max_value] = np.nan

        return lower_band

    # def reset_executor(self):
    #     """检查并重新创建线程池"""
    #     if self.executor_shutdown:
    #         print("线程池已关闭，重新创建线程池...")
    #         self.executor = ThreadPoolExecutor(max_workers=2)
    #         self.executor_shutdown = False

    def sell_logic(self):
        '''
        卖出逻辑
        :param stock_price:
        :param main_date:为多个dict，存有多类数据
        :return:
        '''
        # while self.buy_state_fina is not True:
        # self.reset_executor()  # 检查线程池状态并重新创建

        # 提交任务到线程池
        self.executor.submit(self.high_frequency, self.codes_list)
        self.executor.submit(self.real_time, self.codes_list, 'latest')

        # ---------------------------------------------------------现在逻辑（使用numpy计算）---------------------------------------------------------------

    def close_executor(self):
        """关闭线程池"""
        if not self.executor_shutdown:
            self.executor.shutdown(wait=True)
            self.executor_shutdown = True
            print("线程池已关闭。")

    def judge_temp_time(self):
        self.blacklist.extend(self.codes_list_confirm)
        self.backtime = True
        # self.codes_list_confirm.clear()

    def judge_codes(self, target_list_name):
        """
        用于去除目标列表中黑名单里的股票
        :param target_list_name: 目标列表的属性名（字符串）
        :return:
        """
        if self.backtime:
            target_list = getattr(self, target_list_name)
            new_list = []
            has_removed = False
            for code in target_list:
                if code not in self.blacklist:
                    new_list.append(code)
                else:
                    has_removed = True
            setattr(self, target_list_name, new_list)
            if has_removed:
                self.buy_state = False

    def remove_blacklist(self):
        '''
        用于在限制时间后移除黑名单中股票
        当时间满足限定条件且黑名单有值，清除黑名单值
        :return:
        '''
        self.end_time1 = time.time()
        print(self.end_time1 - self.start_time_list[0])
        if self.limit_time <= self.end_time1 - self.start_time_list[0]:
            self.start_time_list.clear()
            self.blacklist.clear()
        else:
            pass
        # 提示框和实时股线

    def is_ratio_in(self, temp):
        '''
        排除黑名单中的codes_list
        :param temp:
        :return:
        '''
        for blacklist_ in self.blacklist:
            if self.codes_list[temp] == blacklist_:
                self.ratio = None
            else:
                pass

    def sell(self):
        '''
        以下是卖出代码
        :return:
        '''
        if self.state:
            self.user.sell(str(self.stock_symbols), self.prices, self.amounts)


from tkinter import messagebox, ttk
import re
from StockChatBot import StockChatBot




# 以下是UI界面
class StockSearchApp:
    def __init__(self, root):
        self.response = None
        self.chatbot = None
        self.root = root
        self.root.title("300极限低吸系统")
        self.root.geometry("2200x1500")
        self.root.configure(bg="#f5f5f7")
        self.root.attributes("-topmost", True)
        self.input_m = None

        # 初始化 Trader 对象
        self.trader = Trader(r'D:\A-同花顺\代码\sound\io.wav')

        # 设置字体
        font_size = 16
        label_font = ("Helvetica", font_size)
        entry_font = ("Helvetica", font_size)
        button_font = ('宋体', font_size)

        # 自定义样式
        style = ttk.Style()
        style.configure("Apple.TButton", font=button_font, padding=5)
        style.map("Apple.TButton", background=[("active", "#005bb5")])

        # 左侧框架
        left_frame = ttk.Frame(root, padding="5")
        left_frame.grid(row=0, column=0, sticky="nsew")

        # 右侧框架
        right_frame = ttk.Frame(root, padding="5")
        right_frame.grid(row=0, column=1, sticky="nsew")

        # 股票代码输入
        ttk.Label(left_frame, text="输入股票代码:", font=label_font).grid(row=0, column=0, pady=5, sticky="w")
        self.stock_entry = ttk.Entry(left_frame, width=30, font=entry_font)
        self.stock_entry.grid(row=0, column=1, pady=5)
        ttk.Button(left_frame, text="添加", command=self.add_stock_code, style="Apple.TButton").grid(row=0, column=2,
                                                                                                     pady=5, padx=5)

        # 令牌填写框
        ttk.Label(left_frame, text="输入令牌:", font=label_font).grid(row=1, column=0, pady=5, sticky="w")
        self.token_entry = ttk.Entry(left_frame, width=30, font=entry_font)
        self.token_entry.insert(0, "221381")
        self.token_entry.grid(row=1, column=1, pady=5)
        ttk.Button(left_frame, text="设置", command=self.set_token, style="Apple.TButton").grid(row=1, column=2, pady=5,
                                                                                                padx=5)

        # 延时时间输入框
        ttk.Label(left_frame, text="延时时间 (秒):", font=label_font).grid(row=2, column=0, pady=5, sticky="w")
        self.delay_entry = ttk.Entry(left_frame, width=30, font=entry_font)
        self.delay_entry.insert(0, "30")
        self.delay_entry.grid(row=2, column=1, pady=5)
        ttk.Button(left_frame, text="设置", command=self.set_delay_time, style="Apple.TButton").grid(row=2, column=2,
                                                                                                     pady=5, padx=5)

        # 比例阈值输入框
        ttk.Label(left_frame, text="比例阈值:", font=label_font).grid(row=3, column=0, pady=5, sticky="w")
        self.ratio_entry = ttk.Entry(left_frame, width=30, font=entry_font)
        self.ratio_entry.insert(0, "0.005")
        self.ratio_entry.grid(row=3, column=1, pady=5)
        ttk.Button(left_frame, text="设置", command=self.set_ratio_threshold, style="Apple.TButton").grid(row=3,
                                                                                                          column=2,
                                                                                                          pady=5,
                                                                                                          padx=5)

        # 数据展示面板
        self.data_display = tk.Text(left_frame, width=80, height=15, font=entry_font)
        self.data_display.grid(row=4, column=0, columnspan=3, pady=10)

        # # 比例曲线展示面板
        # self.ratio_display = tk.Text(left_frame, width=80, height=22, font=entry_font)
        # self.ratio_display.grid(row=5, column=0, columnspan=3, pady=10)

        # oo
        entry_font = ("Arial", 20)

        # 创建 Figure 和 Axes 对象
        self.fig, self.ax = plt.subplots(figsize=(9, 6))

        # 绘制曲线
        self.plot_ratios()

        # 创建 FigureCanvasTkAgg 对象
        self.canvas = FigureCanvasTkAgg(self.fig, master=left_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=6, column=0, columnspan=3, pady=10)

        # 股票代码列表显示
        self.stock_listbox = tk.Listbox(right_frame, width=30, font=entry_font, selectbackground="#007aff",
                                        selectforeground="white", bg="#ffffff", bd=0, highlightthickness=0)
        self.stock_listbox.grid(row=0, column=0, rowspan=5, padx=10, pady=10, sticky="nsew")

        # 滚动条
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.stock_listbox.yview)
        scrollbar.grid(row=0, column=1, rowspan=5, sticky="ns")
        self.stock_listbox.configure(yscrollcommand=scrollbar.set)

        # AI 接入窗口
        # 输入框
        self.input_entry = tk.Entry(right_frame, font=entry_font, width=30)  # 设置输入框宽度
        self.input_entry.grid(row=0, column=3, columnspan=2, padx=10, pady=10, sticky="ew")

        # 发送按钮
        self.send_button = tk.Button(right_frame, text="发送", font=entry_font, command=self.start_send_message_process,
                                     width=30)  # 设置按钮宽度
        self.send_button.grid(row=1, column=3, columnspan=2, padx=10, pady=10, sticky="ew")

        # 清空记录按钮
        self.clear_button = tk.Button(right_frame, text='清除', font=entry_font, command=self.contant_clear,
                                      width=30)
        self.clear_button.grid(row=3, column=3, columnspan=2, padx=10, pady=10, sticky="ew")

        # 显示 AI 回复的文本框
        self.output_text = tk.Text(right_frame, font=entry_font, height=20, width=30)  # 设置文本框高度和宽度
        self.output_text.grid(row=2, column=3, columnspan=2, padx=10, pady=10, sticky="nsew")

        # 滚动条
        output_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.output_text.yview)
        output_scrollbar.grid(row=2, column=5, sticky="ns")  # 调整滚动条位置，避免与其他组件重叠
        self.output_text.configure(yscrollcommand=output_scrollbar.set)

        # 加载保存的股票代码
        self.load_stock_codes()

        # 按钮
        ttk.Button(right_frame, text="删除选中", command=self.delete_selected_code, style="Apple.TButton").grid(row=5,
                                                                                                                column=0,
                                                                                                                pady=5)
        ttk.Button(right_frame, text="清空全部", command=self.clear_all_codes, style="Apple.TButton").grid(row=6,
                                                                                                           column=0,
                                                                                                           pady=5)
        ttk.Button(right_frame, text="执行买入逻辑", command=self.execute_sell_logic, style="Apple.TButton").grid(row=7,
                                                                                                                  column=0,
                                                                                                                  pady=5)
        ttk.Button(right_frame, text="退出", command=root.destroy, style="Apple.TButton").grid(row=8, column=0,
                                                                                               pady=5)

        # 配置网格权重
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)

    def plot_ratios(self):
        # Clear the current plot
        self.ax.clear()

        # Set the Chinese font
        plt.rcParams[
            'font.family'] = 'SimHei'  # Use SimHei font. You can choose other fonts according to your system, such as 'WenQuanYi Zen Hei'.

        # Solve the problem of negative sign display
        plt.rcParams['axes.unicode_minus'] = False

        # Define the color list
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']

        # Plot the curve for each stock
        for i, (code, ratio) in enumerate(zip(self.trader.codes_list, self.trader.ratio_list_all)):
            color = colors[i % len(colors)]
            self.ax.plot(ratio, label=code, color=color)

        # Set the title and axis labels
        self.ax.set_title("Real-time Stock Ratio Curve")
        self.ax.set_xlabel("Time Point")
        self.ax.set_ylabel("Ratio")

        # Add the legend to the upper right corner
        self.ax.legend(loc='upper right')

        # Automatically adjust the layout
        self.fig.tight_layout()

    @staticmethod
    def convert_md_to_text_and_insert(md_text_str):
        # 检查传入的 Markdown 文本是否为字符串类型
        if not isinstance(md_text_str, str):
            return
        # 将 Markdown 文本转换为 HTML
        html = markdown.markdown(md_text_str)
        # 将 HTML 转换为纯文本
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text()

    def update_display(self):
        try:
            # 更新 Trader 数据
            # 构建要显示的数据
            codes_str = ""
            if self.trader.codes_list is not None:
                codes_str = ", ".join(map(str, self.trader.codes_list))
            data = f"股票代号: {codes_str}\n"

            prices_str = ""
            if self.trader.sorted_selected_elements is not None:
                prices_str = ", ".join(map(str, self.trader.sorted_selected_elements))
            data += f"实时价格: {prices_str}\n"

            ratio_value = ""
            if self.trader.codes_list_confirm is not None:
                ratio_value = ", ".join(map(str, self.trader.codes_list_confirm))
            data += f"达到要求的股票: {ratio_value}\n"

            ratio_value_ = ""
            if self.trader.codes_list_confirm is not None:
                ratio_value_ = ", ".join(map(str, self.trader.ratio_list_all))
            data += f"Ratio_values: {ratio_value_}\n"
            threading.Thread(target=self.trader.output_json_get)

            # 清空文本框
            self.data_display.delete('1.0', tk.END)
            # 插入新数据
            self.data_display.insert(tk.END, data)

        except Exception as e:
            print(f"更新显示时出现错误: {e}")

        # 每 10 秒调用一次 update_display 方法
        self.root.after(1000, self.update_display)

    def add_stock_code(self):
        code = self.stock_entry.get().strip()
        if code:
            if re.match(r'^\d{6}$', code):
                if code.startswith(('00', '01', '02')):
                    full_code = code + '.sz'
                elif code.startswith(('30', '39')):
                    full_code = code + '.sz'
                elif code.startswith(('60', '68')):
                    full_code = code + '.sh'
                else:
                    messagebox.showerror("错误", "无效的股票代码")
                    return
                self.trader.codes_list.append(full_code)
                self.stock_listbox.insert(tk.END, full_code)
                self.save_stock_codes()
            else:
                messagebox.showerror("错误", "请输入 6 位数字的股票代码")

    def get_full_code(self, code):
        if code.startswith(('00', '01', '02', '30', '39')):
            return code + '.sz'
        elif code.startswith(('60', '68')):
            return code + '.sh'
        return None

    def contant_clear(self):
        self.output_text.delete('1.0', tk.END)

    def delete_selected_code(self):
        selected_index = self.stock_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            code = self.stock_listbox.get(index)
            if code in self.trader.codes_list:
                self.trader.codes_list.remove(code)
            self.stock_listbox.delete(index)
            self.save_stock_codes()
        else:
            messagebox.showerror("错误", "请先选择要删除的代码")

    def save_stock_codes(self):
        with open('stock_codes1.json', 'w') as f:
            json.dump(self.trader.codes_list, f)

    def save_refresh_tokens(self):
        with open('refresh_tokens.json', 'w') as f:
            json.dump(self.trader.refreshtoken, f)

    def load_stock_codes(self):
        if os.path.exists('stock_codes1.json'):
            with open('stock_codes1.json', 'r') as f:
                codes = json.load(f)
                for code in codes:
                    self.trader.codes_list.append(code)
                    self.stock_listbox.insert(tk.END, code)

    def load_refresh_tokens(self):
        if os.path.exists('refresh_tokens.json'):
            with open('refresh_tokens.json', 'r') as f:
                refresh_tokens = json.load(f)

    def clear_all_codes(self):
        self.trader.codes_list.clear()
        self.stock_listbox.delete(0, tk.END)
        self.save_stock_codes()
        messagebox.showinfo("成功", "已清空所有股票代码")

    def set_token(self):
        self.trader.refreshtoken = self.token_entry.get().strip()
        if self.trader.refreshtoken:
            # 这里可以添加令牌验证逻辑
            messagebox.showinfo("成功", f"令牌已设置为: {self.trader.refreshtoken}")
        else:
            messagebox.showerror("错误", "请输入有效的令牌")

    def set_delay_time(self):
        try:
            delay_time = float(self.delay_entry.get())
            if delay_time >= 0:
                self.trader.limit_time = delay_time
                messagebox.showinfo("成功", f"延时时间已设置为 {delay_time} 秒")
            else:
                messagebox.showerror("错误", "延时时间不能为负数")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def set_ratio_threshold(self):
        try:
            ratio_threshold = float(self.ratio_entry.get())
            self.trader.ratio_threshold = ratio_threshold
            messagebox.showinfo("成功", f"比例阈值已设置为 {ratio_threshold}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def execute_sell_logic(self):
        if self.trader.codes_list:
            threading.Thread(target=self.trader.sell_logic).start()
            messagebox.showinfo("反馈", "已成功执行")
            # 执行显示控件
            threading.Thread(target=self.update_display).start()
        else:
            messagebox.showerror("错误", "请先添加股票代码")

    def send_message(self):
        messagebox.showinfo('提示', '执行成功')
        message = self.input_entry.get()
        self.input_m = message
        # 初始化 StockChatBot对象
        self.chatbot = StockChatBot(input_m=self.input_m)
        # 这里可以添加调用 AI 接口的代码
        self.chatbot.run()
        self.response = self.chatbot.assistant_response_content
        self.output_text.insert(tk.END, self.convert_md_to_text_and_insert(self.response,) + "\n")
        self.input_entry.delete(0, tk.END)
        return self.response

    def start_send_message_process(self):
        # 创建一个新的进程来运行 send_message 方法
        process = threading.Thread(target=self.send_message)
        process.start()


# if __name__ == '__main__':
#     trader = Trader(r'D:\A-同花顺\代码\sound\io.wav')
#     trader.codes_list = ['002741.sz', '300657.sz', '300068.sz']
#     trader.sell_logic()
if __name__ == '__main__':
    root = tk.Tk()
    app = StockSearchApp(root)
    root.mainloop()
