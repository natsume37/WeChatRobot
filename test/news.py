import json
import time
from datetime import datetime

import requests

url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6&sign=9f8797a1f4de66c2370f7a03990d2737"
data = {"type": "telegram", "keyword": "你需要知道的隔夜全球要闻", "page": 0, "rn": 20, "os": "web", "sv": "8.4.6",
        "app": "CailianpressWeb"}
header = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}
rsp = requests.post(url=url, headers=header, data=data)
data = json.loads(rsp.text)["data"]["telegram"]["data"][0]
news = data["descr"]
timestamp = data["time"]
ts = time.localtime(timestamp)
weekday_news = datetime(*ts[:6]).weekday()

print(rsp.json())
# print(news)
