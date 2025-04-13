import os
import random
import json
import pandas as pd

# 定义文件路径
SCORE_FILE = "chengyu_scores.json"
CONTEXT_FILE = "chengyu_context.json"
ERROR_FILE = "chengyu_errors.json"  # 记录用户错误次数
FAILURE_COUNT_FILE = "failure_count.json"  # 记录用户失败次数


class Chengyu:
    def __init__(self) -> None:
        # 获取当前脚本路径，读取数据文件
        root = os.path.dirname(os.path.abspath(__file__))
        self.df = pd.read_csv(f"{root}/chengyu.csv", delimiter="\t")
        self.cys, self.zis, self.yins = self._build_data()
        self.scores = self.load_json(SCORE_FILE)
        self.context = self.load_json(CONTEXT_FILE)
        self.errors = self.load_json(ERROR_FILE)  # 加载错误次数
        self.failure_count = self.load_json(FAILURE_COUNT_FILE)  # 加载失败次数

    def _build_data(self):
        # 处理成语数据
        df = self.df.copy()
        df["shouzi"] = df["chengyu"].apply(lambda x: x[0])  # 成语首字
        df["mozi"] = df["chengyu"].apply(lambda x: x[-1])  # 成语末字
        df["shouyin"] = df["pingyin"].apply(lambda x: x.split(" ")[0])  # 成语首音
        df["moyin"] = df["pingyin"].apply(lambda x: x.split(" ")[-1])  # 成语末音

        # 构建字典数据
        cys = dict(zip(df["chengyu"], df["moyin"]))  # 成语与拼音末字的映射
        zis = df.groupby("shouzi").agg({"chengyu": set})["chengyu"].to_dict()  # 按首字分组
        yins = df.groupby("shouyin").agg({"chengyu": set})["chengyu"].to_dict()  # 按首音分组

        return cys, zis, yins

    def load_json(self, filename):
        # 加载JSON文件
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_json(self, filename, data):
        # 保存JSON文件
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def isChengyu(self, cy: str) -> bool:
        """检查给定的成语是否在字典中"""
        return cy in self.cys

    def getNext(self, wxid: str, cy: str, use_pinyin=True):
        """
        判断用户输入的成语与当前接龙成语是否可以接龙
        如果能接龙返回下一个成语，并保存到上下文
        如果不能接龙返回 False
        :param wxid: 用户的微信ID
        :param cy: 用户输入的成语
        :param use_pinyin: 是否启用谐音接龙，默认为 True
        """
        # 获取当前接龙的成语
        current_chengyu = self.context.get(wxid, None)

        # 如果当前没有接龙的成语，随机选一个成语
        if not current_chengyu:
            # 系统选择一个随机成语，作为初始状态
            current_chengyu = random.choice(list(self.cys.keys()))
            self.context[wxid] = current_chengyu  # 保存用户上下文
            self.save_json(CONTEXT_FILE, self.context)  # 保存上下文到文件
            return True, f"当前没有进行中的接龙，系统随机选择了一个成语：{current_chengyu}，请继续接龙。"

        # 判断用户输入的成语是否存在于字典中
        if not self.isChengyu(cy):  # 如果输入的成语不在字典中，返回 False
            return False, "你输入的成语不在字典库中，请重新输入。"

        # 当前成语的最后一个字
        last_char_of_current = current_chengyu[-1]

        # 用户输入的成语的第一个字
        first_char_of_input = cy[0]

        # 如果没有启用拼音接龙，继续按照字形接龙规则
        if last_char_of_current == first_char_of_input:
            next_chengyu = self.getNextWord(cy)
            if next_chengyu:
                self.context[wxid] = next_chengyu
                self.save_json(CONTEXT_FILE, self.context)
                return True, next_chengyu
            else:
                return False, "没有找到可以接龙的成语。"
        elif use_pinyin:
            last_pinyin_of_current = self.cys.get(current_chengyu)
            first_pinyin_of_input = self.cys.get(cy)

            # 判断拼音首音是否相同
            if last_pinyin_of_current == first_pinyin_of_input:
                next_chengyu = self.getNextWord(cy)
                if next_chengyu:
                    self.context[wxid] = next_chengyu
                    self.save_json(CONTEXT_FILE, self.context)
                    return True, next_chengyu
                else:
                    return False, "没有找到可以接龙的成语。"
            else:
                return False, f"当前成语为：{current_chengyu}，{cy}无法接龙，请尝试其他成语。"

    def getNextWord(self, cy: str) -> str:
        """获取下一个可以接龙的成语"""
        zi = cy[-1]
        ansers = list(self.zis.get(zi, {}))
        if cy in ansers:
            ansers.remove(cy)

        if ansers:
            return random.choice(ansers)

        yin = self.cys.get(cy)
        ansers = list(self.yins.get(yin, {}))
        if cy in ansers:
            ansers.remove(cy)

        return random.choice(ansers) if ansers else None

    def can_connect(self, cy1: str, cy2: str) -> bool:
        """判断两个成语是否可以接龙"""
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


cy = Chengyu()
# 测试代码
if __name__ == "__main__":
    game = Chengyu()
    wxid = "user_123"

    # 测试接龙判断
    print(game.getNext(wxid, "老妪能解", use_pinyin=True))  # 启用谐音接龙
