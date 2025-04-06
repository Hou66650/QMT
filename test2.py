import datetime


class TradingTimeCalculator:
    def __init__(self):
        # 定义早市和午市的时间范围
        self.morning_start = datetime.time(9, 30)
        self.morning_end = datetime.time(11, 30)
        self.afternoon_start = datetime.time(13, 0)
        self.afternoon_end = datetime.time(15, 0)
        # 早市和午市的时长（分钟）
        self.morning_duration = 120
        self.afternoon_duration = 120
        self.total_trading_duration = self.morning_duration + self.afternoon_duration

    def is_weekday(self, date):
        """判断是否为工作日"""
        return date.weekday() < 5

    def calculate_previous_time(self, input_time_str, target_minutes):
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


def adjust_minutes_to_15_min_interval(time_str):
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
    new_time_str = new_dt.strftime('%Y-%m-%d %H:%M:%S')

    return new_time_str


# 测试
calculator = TradingTimeCalculator()
input_time = '2025-02-28 9:32:00'
target_minutes = 285
result = calculator.calculate_previous_time(input_time, target_minutes)
new_time_str = adjust_minutes_to_15_min_interval(result)
print(result)
print(new_time_str)
