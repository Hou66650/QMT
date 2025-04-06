import json
import openai
import time
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StockChatBot:
    def __init__(self, input_m):
        # 基础配置
        self.base_url = "https://api.wlai.vip/v1"
        self.api_key = "sk-RHOoG7f0dNDwQ6yQvmHkfz8N7QHXWTJcQIteGNrI7loI1Rv6"
        self.json_file_path = r'D:\A-同花顺\代码\json/output.json'
        self.ratio_explanation_path = r'D:\A-同花顺\代码\json/ratio_explanation.json'

        # 初始化 OpenAI 客户端
        self.client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        # 存储文件路径
        self.json_file_path = self.json_file_path
        self.ratio_explanation_path = self.ratio_explanation_path

        # 初始化消息列表
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

        # 加载 JSON 数据
        self.data = self.load_json_data()
        if not self.data:
            logging.error("Failed to load JSON data.")
            return

        # 创建股票代码索引
        self.code_to_data = self.create_code_index()

        # 加载比率解释
        self.ratio_explanation = self.load_ratio_explanation()
        if not self.ratio_explanation:
            logging.error("Failed to load ratio explanation.")
            return

        # 将比率解释添加到系统消息中
        self.add_ratio_explanation_to_messages()

        # 存储用户输入
        self.input_m = input_m
        self.assistant_response_content = None

    def load_json_data(self):
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"JSON 文件 {self.json_file_path} 未找到。")
            return []
        except json.JSONDecodeError:
            logging.error(f"无法解析 JSON 文件 {self.json_file_path}。")
            return []

    def create_code_index(self):
        code_index = {}
        for item in self.data:
            stock_code = item.get('股票代码')
            if stock_code:
                code_index[stock_code] = item
        return code_index

    def load_ratio_explanation(self):
        try:
            with open(self.ratio_explanation_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"JSON 文件 {self.ratio_explanation_path} 未找到。")
            return {}
        except json.JSONDecodeError:
            logging.error(f"无法解析 JSON 文件 {self.ratio_explanation_path}。")
            return {}

    def add_ratio_explanation_to_messages(self):
        explanation = self.ratio_explanation.get('text', '')
        if explanation:
            self.messages[0]["content"] += f" ratio值是指: {explanation}"

    def run(self):
        user_input = self.input_m
        # 简单假设用户输入的股票代码是数字，可根据实际情况调整
        stock_code = ''.join(filter(str.isdigit, user_input))

        user_message = user_input
        if stock_code:
            selected_item = self.code_to_data.get(stock_code)
            if selected_item:
                ratio_values = selected_item.get('ratio值', [])
                ratio_str = ', '.join(map(str, ratio_values))
                user_message = f"股票代码: {stock_code}, ratio值: {ratio_str}。{user_input}"
            else:
                logging.warning(f"未找到股票代码 {stock_code} 对应的信息。")
        else:
            logging.warning("未从输入中识别到股票代码。")

        self.messages.append({"role": "user", "content": user_message})

        try:
            # 重试机制
            max_retries = 3
            retries = 0
            while retries < max_retries:
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-2024-11-20",
                        messages=self.messages,
                        temperature=1
                    )
                    break
                except openai.RateLimitError:
                    logging.warning("Rate limit exceeded. Retrying in 10 seconds...")
                    time.sleep(10)
                    retries += 1
                except openai.OpenAIError as e:
                    logging.error(f"OpenAI API 错误: {e}")
                    retries += 1

            if retries == max_retries:
                logging.error("Max retries reached. Unable to get a response from the API.")
                return

            if response and hasattr(response, 'choices'):
                if response.choices:
                    self.assistant_response_content = response.choices[0].message.content
                    self.messages.append({"role": "assistant", "content": self.assistant_response_content})
                else:
                    logging.warning("No choices available in the response.")
            else:
                logging.warning("Invalid response or no choices found.")

        except Exception as e:
            logging.error(f"其他错误: {e}")

    def save_conversation(self, file_path):
        """
        将对话保存到 JSON 文件中
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.messages, file, ensure_ascii=False, indent=4)
            logging.info(f"Conversation saved to {file_path}")
        except Exception as e:
            logging.error(f"Failed to save conversation: {e}")

    def get_conversation_history(self):
        """
        返回对话历史
        """
        return self.messages