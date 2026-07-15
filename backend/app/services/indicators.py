from app.schemas import HistoryBar


def add_bollinger_bands(items: list[HistoryBar], window: int = 20, multiplier: float = 2) -> list[HistoryBar]:
    closes: list[float] = []
    for item in items:
        closes.append(item.close)
        if len(closes) >= window:
            values = closes[-window:]
            middle = sum(values) / window
            variance = sum((value - middle) ** 2 for value in values) / window
            deviation = variance ** 0.5
            item.middle_band = round(middle, 3)
            item.upper_band = round(middle + multiplier * deviation, 3)
            item.lower_band = round(middle - multiplier * deviation, 3)
    return items


def strategy_signal(items: list[HistoryBar]) -> tuple[str, str]:
    if not items or items[-1].lower_band is None:
        return "观察", "历史数据不足 20 个周期"
    latest = items[-1]
    if latest.close <= latest.lower_band:
        return "关注低吸", "收盘价触及或跌破布林下轨"
    if latest.close >= (latest.upper_band or latest.close + 1):
        return "注意回撤", "收盘价触及或突破布林上轨"
    return "中性", "价格运行在布林带区间内"
