import smtplib
import random
import tkinter as tk
from tkinter import messagebox, ttk
from email.mime.text import MIMEText
from email.header import Header
import time

# 白名单QQ邮箱列表
WHITELIST_EMAILS = [
    "123456789@qq.com", "987654321@qq.com", '1795890242@qq.com',
    '2870942595@qq.com', '2658088858@qq.com', '1473272757@qq.com'
]

# 验证码有效期（5分钟）
VERIFICATION_CODE_EXPIRY = 5 * 60  # 5分钟

def generate_verification_code():
    """生成6位随机验证码"""
    return ''.join(random.choices('0123456789', k=6))

def send_verification_code(email, code):
    """发送验证码到邮箱"""
    smtp_server = "smtp.qq.com"
    smtp_port = 465
    sender_email = "1795890242@qq.com"  # 发件人邮箱
    sender_password = "esfkjcgjmzhgccef"  # 发件人邮箱的授权码

    subject = "验证码"
    body = f"您的验证码是：{code}，请在程序中输入该验证码。验证码有效期为5分钟。"

    message = MIMEText(body, 'plain', 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')
    message['From'] = sender_email
    message['To'] = email

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False

def is_email_in_whitelist(email):
    """验证邮箱是否在白名单中"""
    return email in WHITELIST_EMAILS

class VerificationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("验证码验证系统")
        self.root.geometry("400x350")
        self.root.configure(bg="#f0f0f0")  # 设置背景颜色

        self.verification_code = None
        self.email = None
        self.send_time = None  # 验证码发送时间

        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="请输入QQ邮箱:", font=("Arial", 12)).pack(pady=10)
        self.entry_email = ttk.Entry(frame, width=30)
        self.entry_email.pack(pady=10)

        ttk.Button(frame, text="发送验证码", command=self.send_code).pack(pady=5)
        ttk.Button(frame, text="重新发送验证码", command=self.resend_code).pack(pady=5)

        ttk.Label(frame, text="请输入验证码:", font=("Arial", 12)).pack(pady=10)
        self.entry_code = ttk.Entry(frame, width=30)
        self.entry_code.pack(pady=10)

        ttk.Button(frame, text="验证", command=self.verify_code).pack(pady=10)

    def send_code(self):
        """发送验证码"""
        email = self.entry_email.get().strip()
        if not email:
            messagebox.showerror("错误", "请输入QQ邮箱")
            return

        if not is_email_in_whitelist(email):
            messagebox.showerror("错误", "该邮箱不在白名单中")
            return

        self.verification_code = generate_verification_code()
        self.email = email
        self.send_time = time.time()  # 记录发送时间

        if send_verification_code(email, self.verification_code):
            messagebox.showinfo("成功", "验证码已发送到您的邮箱，请查收")
        else:
            messagebox.showerror("错误", "验证码发送失败，请检查邮箱是否正确")

    def resend_code(self):
        """重新发送验证码"""
        if not self.email:
            messagebox.showerror("错误", "请先输入邮箱并发送验证码")
            return

        self.verification_code = generate_verification_code()
        self.send_time = time.time()  # 更新发送时间

        if send_verification_code(self.email, self.verification_code):
            messagebox.showinfo("成功", "新的验证码已发送到您的邮箱，请查收")
        else:
            messagebox.showerror("错误", "验证码发送失败，请检查邮箱是否正确")

    def verify_code(self):
        """验证验证码"""
        user_code = self.entry_code.get().strip()
        if not user_code:
            messagebox.showerror("错误", "请输入验证码")
            return

        if self.verification_code is None:
            messagebox.showerror("错误", "请先发送验证码")
            return

        current_time = time.time()
        if current_time - self.send_time > VERIFICATION_CODE_EXPIRY:
            messagebox.showerror("错误", "验证码已过期，请重新获取")
            return

        if user_code == self.verification_code:
            messagebox.showinfo("成功", "验证码正确，允许进入")
            # 这里可以添加后续逻辑
        else:
            messagebox.showerror("错误", "验证码错误，请重新输入")

if __name__ == "__main__":
    root = tk.Tk()
    app = VerificationApp(root)
    root.mainloop()
