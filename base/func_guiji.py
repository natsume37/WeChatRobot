import requests


class ChatBot:
    def __init__(self, model_type="Qwen/QwQ-32B", prompt="你是一个AI助手、积极的帮助别人解答问题。",
                 api_key=None, user_qs=None):
        self.model_type = model_type
        self.prompt = prompt
        self.api_key = api_key
        self.user_qs = user_qs
        self.url = "https://api.siliconflow.cn/v1/chat/completions"

    def __repr__(self):
        return '硅基流动Bot，支持类型：https://cloud.siliconflow.cn/models'

    def get_response(self):
        if not self.api_key or not self.user_qs:
            return "API Key 或用户问题 (user_qs) 不能为空"

        payload = {
            "model": self.model_type,
            "stream": False,
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "messages": [
                {
                    "content": self.prompt,
                    "role": "system"
                },
                {
                    "content": self.user_qs,
                    "role": "user"
                }
            ],
            "stop": "",
            "tools": []
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(self.url, json=payload, headers=headers).json()
        res = response["choices"][0]["message"]["content"]
        return res


# 示例用法
if __name__ == "__main__":
    api_key = "sk-"  # 替换为你的实际API Key
    user_qs = "你会什么？"

    chatbot = ChatBot(api_key=api_key, user_qs=user_qs)
    response = chatbot.get_response()
    print(response)
