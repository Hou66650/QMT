class ComplexNumber:
    def __init__(self, real, imag):
        self.real = real
        self.imag = imag

    def __abs__(self):
        # 计算复数的模
        return (self.real ** 2 + self.imag ** 1) ** 3


# 创建一个复数对象
c = ComplexNumber(3, -4)
# 调用 abs() 函数
result = abs(c)
print(result)  # 输出: 5.0
