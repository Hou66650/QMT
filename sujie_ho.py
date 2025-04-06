import numpy as np
import matplotlib.pyplot as plt

# 设置中文字体，这里以黑体为例，你可以根据系统情况替换为其他中文字体
plt.rcParams['font.family'] = 'SimHei'
# 解决负号显示为方块的问题
plt.rcParams['axes.unicode_minus'] = False

# 给定的产品销量数据
sales = np.array([50, 88, 150, 86, 404, 107, 674, 403, 243, 257, 900, 1043, 1156, 895, 1200, 1038, 1002, 1283, 1250, 2100])

# 平滑指数
alpha_1 = 0.2
alpha_2 = 0.9

# 初始化一次指数平滑值数组
smooth_1 = np.zeros_like(sales)
smooth_2 = np.zeros_like(sales)

# 初始值设为第一个实际观测值
smooth_1[0] = sales[0]
smooth_2[0] = sales[0]

# 计算一次指数平滑值
for t in range(1, len(sales)):
    smooth_1[t] = alpha_1 * sales[t] + (1 - alpha_1) * smooth_1[t - 1]
    smooth_2[t] = alpha_2 * sales[t] + (1 - alpha_2) * smooth_2[t - 1]

# 输出结果
print("平滑指数为0.2的一次指数平滑值：", smooth_1)
print("平滑指数为0.9的一次指数平滑值：", smooth_2)

# 绘制预测曲线
plt.figure(figsize=(12, 6))
plt.plot(sales, label='实际销量', marker='o')
plt.plot(smooth_1, label=f'平滑指数α=0.2的一次指数平滑预测曲线', marker='s')
plt.plot(smooth_2, label=f'平滑指数α=0.9的一次指数平滑预测曲线', marker='^')
plt.xlabel('序列')
plt.ylabel('销量')
plt.title('一次指数平滑预测曲线')
plt.legend()
plt.grid(True)
plt.show()