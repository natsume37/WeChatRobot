import os
import random
import json
import pandas as pd

SCORE_FILE = "chengyu_scores.json"
CONTEXT_FILE = "chengyu_context.json"
ERROR_FILE = "chengyu_errors.json"  # 记录用户错误次数
FAILURE_COUNT_FILE = "failure_count.json"  # 记录用户失败次数


class Chengyu:
    def __init__(self) -> None:
        root = os.path.dirname(os.path.abspath(__file__))
        self.df = pd.read_csv(f"{root}/chengyu.csv", delimiter="\t")
        self.cys, self.zis, self.yins = self._build_data()
        self.scores = self.load_json(SCORE_FILE)
        self.context = self.load_json(CONTEXT_FILE)
        self.errors = self.load_json(ERROR_FILE)  # 加载错误次数
        self.failure_count = self.load_json(FAILURE_COUNT_FILE)  # 加载失败次数

    def _build_data(self):
        df = self.df.copy()
        df["shouzi"] = df["chengyu"].apply(lambda x: x[0])
        df["mozi"] = df["chengyu"].apply(lambda x: x[-1])
        df["shouyin"] = df["pingyin"].apply(lambda x: x.split(" ")[0])
        df["moyin"] = df["pingyin"].apply(lambda x: x.split(" ")[-1])

        cys = dict(zip(df["chengyu"], df["moyin"]))
        zis = df.groupby("shouzi").agg({"chengyu": set})["chengyu"].to_dict()
        yins = df.groupby("shouyin").agg({"chengyu": set})["chengyu"].to_dict()

        return cys, zis, yins

    def load_json(self, filename):
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_json(self, filename, data):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get_score(self, wxid):
        return self.scores.get(wxid, 0)

    def add_score(self, wxid, points=1):
        self.scores[wxid] = self.get_score(wxid) + points
        self.save_json(SCORE_FILE, self.scores)

    def isChengyu(self, cy: str) -> bool:
        return cy in self.cys

    def getNext(self, cy: str, tongyin: bool = True) -> str:
        zi = cy[-1]
        ansers = list(self.zis.get(zi, {}))
        if cy in ansers:
            ansers.remove(cy)

        if ansers:
            return random.choice(ansers)

        if tongyin:
            yin = self.cys.get(cy)
            ansers = list(self.yins.get(yin, {}))
            if cy in ansers:
                ansers.remove(cy)

        return random.choice(ansers) if ansers else None

    def can_connect(self, cy1: str, cy2: str) -> bool:
        return cy1[-1] == cy2[0] if self.isChengyu(cy1) and self.isChengyu(cy2) else False

    def reset_current_chengyu(self, wxid):
        random_chengyu = random.choice(list(self.cys.keys()))
        self.context[wxid] = random_chengyu
        self.errors[wxid] = 0  # 重置错误次数
        self.failure_count[wxid] = 0  # 重置失败次数
        self.save_json(CONTEXT_FILE, self.context)
        self.save_json(ERROR_FILE, self.errors)
        self.save_json(FAILURE_COUNT_FILE, self.failure_count)  # 保存失败次数
        return f"当前接龙成语已重置为：{random_chengyu}，请继续接龙。"

    def query_current_chengyu(self, wxid):
        return f"当前接龙成语是：{self.context.get(wxid, '暂无')}"

    def getMeaning(self, cy: str) -> str:
        res = self.df[self.df["chengyu"] == cy].to_dict(orient="records")
        if res:
            res = res[0]
            return f"{res['chengyu']}\n{res['pingyin']}\n{res['jieshi']}\n出处：{res['chuchu']}\n例子：{res['lizi']}"
        return "未找到该成语的解释。"





cy = Chengyu()

# 测试代码
if __name__ == "__main__":
    game = Chengyu()
    wxid = "user_123"
    print(game.reset_current_chengyu(wxid))
    print(game.toChengyu("马到成功", wxid))  # 正确的接龙
    print(game.toChengyu("牛气冲天", wxid))  # 错误的接龙
    print(game.toChengyu("风和日丽", wxid))  # 错误的接龙
    print(game.toChengyu("画蛇添足", wxid))  # 错误的接龙，应该重置成语
