import tkinter as tk
from tkinter import filedialog, messagebox
import re

class Trader:
    def __init__(self):
        self.codes_list = []

    def sell_logic(self):
        print("执行卖出逻辑")
        print("股票代码列表:", self.codes_list)

class StockSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("股票交易助手")

        # 股票代码输入
        self.stock_label = tk.Label(root, text="输入股票代码:")
        self.stock_label.pack()
        self.stock_entry = tk.Entry(root, width=50)
        self.stock_entry.pack()
        self.add_stock_button = tk.Button(root, text="添加股票代码", command=self.add_stock_code)
        self.add_stock_button.pack()

        # 股票代码列表显示
        self.stock_listbox = tk.Listbox(root, width=50)
        self.stock_listbox.pack()

        # 执行交易逻辑按钮
        self.execute_button = tk.Button(root, text="执行卖出逻辑", command=self.execute_sell_logic)
        self.execute_button.pack()

        # 退出按钮
        self.exit_button = tk.Button(root, text="退出", command=self.root.destroy)
        self.exit_button.pack()

        # 初始化 Trader 对象
        self.trader = Trader()

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
            else:
                messagebox.showerror("错误", "请输入 6 位数字的股票代码")

    def execute_sell_logic(self):
        if self.trader.codes_list:
            self.trader.sell_logic()
        else:
            messagebox.showerror("错误", "请先添加股票代码")

if __name__ == '__main__':
    root = tk.Tk()
    app = StockSearchApp(root)
    root.mainloop()

