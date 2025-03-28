# -*- coding: utf-8 -*-
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from queue import Empty
from threading import Thread
from base.func_zhipu import ZhiPu

from wcferry import Wcf, WxMsg

from base.func_bard import BardAssistant
from base.func_chatglm import ChatGLM
from base.func_ollama import Ollama
from base.func_chatgpt import ChatGPT
from base.func_chengyu import cy, CONTEXT_FILE
from base.func_weather import Weather
from base.func_news import News
from base.func_tigerbot import TigerBot
from base.func_xinghuo_web import XinghuoWeb
from configuration import Config
from constants import ChatType
from job_mgmt import Job

__version__ = "39.2.4.0"

BOT_FUNC = {
    1: "成语接龙（没反应代表不是成语）：#开头",
    2: "成语答疑：？开头",
    3: "积分排行榜：%查询",
    4: "成语重置：#重置",
}


class Robot(Job):
    """个性化自己的机器人
    """

    def __init__(self, config: Config, wcf: Wcf, chat_type: int) -> None:
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.getAllContacts()
        self._msg_timestamps = []

        if ChatType.is_in_chat_types(chat_type):
            if chat_type == ChatType.TIGER_BOT.value and TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif chat_type == ChatType.CHATGPT.value and ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif chat_type == ChatType.XINGHUO_WEB.value and XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif chat_type == ChatType.CHATGLM.value and ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif chat_type == ChatType.BardAssistant.value and BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif chat_type == ChatType.ZhiPu.value and ZhiPu.value_check(self.config.ZhiPu):
                self.chat = ZhiPu(self.config.ZhiPu)
            elif chat_type == ChatType.OLLAMA.value and Ollama.value_check(self.config.OLLAMA):
                self.chat = Ollama(self.config.OLLAMA)
            else:
                self.LOG.warning("未配置模型")
                self.chat = None
        else:
            if TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif Ollama.value_check(self.config.OLLAMA):
                self.chat = Ollama(self.config.OLLAMA)
            elif XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif ZhiPu.value_check(self.config.ZhiPu):
                self.chat = ZhiPu(self.config.ZhiPu)
            else:
                self.LOG.warning("未配置模型")
                self.chat = None

        self.LOG.info(f"已选择: {self.chat}")

    @staticmethod
    def value_check(args: dict) -> bool:
        if args:
            return all(value is not None for key, value in args.items() if key != 'proxy')
        return False

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        return self.toChitchat(msg)

    def toChengyu(self, msg: WxMsg) -> bool:
        """
        处理成语查询/接龙消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        status = False
        texts = re.findall(r"^([#?？!！%])(.*)$", msg.content)

        if texts:
            flag, text = texts[0]
            wxid = msg.sender  # 以房间ID或用户ID区分不同用户的接龙状态

            if flag == "#":  # 接龙
                if text == "菜单":
                    output = "\n".join(map(lambda x: json.dumps(BOT_FUNC[x], ensure_ascii=False), BOT_FUNC))
                    self.sendTextMsg(msg=output, receiver=msg.roomid, at_list=msg.sender)
                elif text == "重置":
                    res = cy.reset_current_chengyu(msg.sender)
                    self.sendTextMsg(msg=res, receiver=msg.roomid, at_list=msg.sender)
                elif cy.isChengyu(text):
                    last_chengyu = cy.context.get(wxid, None)

                    if last_chengyu:  # 用户正在接龙
                        if cy.can_connect(last_chengyu, text):
                            cy.add_score(wxid, 10)  # 用户正确接龙，增加积分
                            cy.context[wxid] = text  # 更新当前成语
                            cy.save_json(CONTEXT_FILE, cy.context)  # 保存更新后的成语上下文
                            self.sendTextMsg(
                                f"接龙成功！请继续接龙：{cy.getNext(text)} 🎉 +10积分，当前积分：{cy.get_score(wxid)}",
                                msg.roomid)
                            status = True
                        else:
                            # 用户失败，增加失败次数
                            cy.failure_count[wxid] = cy.failure_count.get(wxid, 0) + 1

                            if cy.failure_count[wxid] >= 3:
                                # 失败次数达到三次，更新当前成语并重置失败计数
                                cy.update_current_chengyu(wxid)
                                self.sendTextMsg(f"接龙失败次数过多，当前成语已更新。新的成语是：{cy.context[wxid]}",
                                                 msg.roomid)
                            else:
                                self.sendTextMsg(f"接龙失败！{text} 不能接在 {last_chengyu} 后面，请重新开始。",
                                                 msg.roomid)
                    else:
                        # 用户未在接龙状态，随机生成一个成语
                        next_chengyu = cy.getNext(text)
                        if next_chengyu:
                            cy.context[wxid] = next_chengyu
                            cy.save_json(CONTEXT_FILE, cy.context)  # 保存更新后的成语上下文
                            self.sendTextMsg(f"接龙开始！第一个成语是：{next_chengyu}，请继续接龙。", msg.roomid)
                            status = True

            elif flag in ["?", "？"]:  # 查成语含义
                if cy.isChengyu(text):
                    rsp = cy.getMeaning(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True

            elif msg.content in ["!成语", "！成语"]:  # 查询当前成语
                last_chengyu = cy.context.get(wxid, None)
                if last_chengyu:
                    self.sendTextMsg(f"当前接龙成语是：{last_chengyu}", msg.roomid)
                else:
                    self.sendTextMsg("您目前没有进行接龙。", msg.roomid)
                status = True
            elif flag in ["%", "%"]:
                if text == "查询":
                    res = self.get_leaderboard(msg)
                    self.sendTextMsg(res, msg.roomid, at_list=msg.sender)
        return status

    def get_leaderboard(self, msg: WxMsg):
        # 排序并获取前 5 名
        leaderboard = sorted(cy.scores.items(), key=lambda x: x[1], reverse=True)[:5]

        # 查找用户的排名
        user_rank = next(((idx + 1, score) for idx, (user_id, score) in enumerate(leaderboard) if user_id == msg.sender),
                         None)
        # f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"
        # 格式化输出
        leaderboard_str = "\n".join(
            [f"第{idx + 1}名：@{self.wcf.get_alias_in_chatroom(user_id,msg.roomid )} - {score}分" for idx, (user_id, score) in enumerate(leaderboard)])

        if user_rank:
            user_rank_str = f"您的排名：第{user_rank[0]}名 - {user_rank[1]}分"
        else:
            user_rank_str = "您不在前 5 名内。"

        return f"排行榜前 5 名：\n{leaderboard_str}\n\n{user_rank_str}"

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT
        """
        if not self.chat:  # 没接 ChatGPT，固定回复
            rsp = "你@我干嘛？"
        else:  # 接了 ChatGPT，智能回复
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            rsp = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))

        if rsp:
            if msg.from_group():
                self.sendTextMsg(rsp, msg.roomid, msg.sender)
            else:
                self.sendTextMsg(rsp, msg.sender)

            return True
        else:
            self.LOG.error(f"无法从 ChatGPT 获得答案")
            return False

    def processMsg(self, msg: WxMsg) -> None:
        """当接收到消息的时候，会调用本方法。如果不实现本方法，则打印原始消息。
        此处可进行自定义发送的内容,如通过 msg.content 关键字自动获取当前天气信息，并发送到对应的群组@发送者
        群号：msg.roomid  微信ID：msg.sender  消息内容：msg.content
        content = "xx天气信息为："
        receivers = msg.roomid
        self.sendTextMsg(content, receivers, msg.sender)
        """

        # 群聊消息
        if msg.from_group():
            # 如果在群里被 @
            if msg.roomid not in self.config.GROUPS:  # 不在配置的响应的群列表里，忽略
                return

            if msg.is_at(self.wxid):  # 被@
                self.toAt(msg)
            else:  # 其他消息
                self.toChengyu(msg)

            return  # 处理完群聊信息，后面就不需要处理了

        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)

        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)

        elif msg.type == 0x01:  # 文本消息
            # 让配置加载更灵活，自己可以更新配置。也可以利用定时任务更新。
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新")
            else:
                self.toChitchat(msg)  # 闲聊

    def onMsg(self, msg: WxMsg) -> int:
        try:
            self.LOG.info(msg)  # 打印信息
            self.processMsg(msg)
        except Exception as e:
            self.LOG.error(e)

        return 0

    def enableRecvMsg(self) -> None:
        self.wcf.enable_recv_msg(self.onMsg)

    def enableReceivingMsg(self) -> None:
        def innerProcessMsg(wcf: Wcf):
            while wcf.is_receiving_msg():
                try:
                    msg = wcf.get_msg()
                    self.LOG.info(msg)
                    self.processMsg(msg)
                except Empty:
                    continue  # Empty message
                except Exception as e:
                    self.LOG.error(f"Receiving message error: {e}")

        self.wcf.enable_receiving_msg()
        Thread(target=innerProcessMsg, name="GetMessage", args=(self.wcf,), daemon=True).start()

    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # 随机延迟0.3-1.3秒，并且一分钟内发送限制
        time.sleep(float(str(time.time()).split('.')[-1][-2:]) / 100.0 + 0.3)
        now = time.time()
        if self.config.SEND_RATE_LIMIT > 0:
            # 清除超过1分钟的记录
            self._msg_timestamps = [t for t in self._msg_timestamps if now - t < 60]
            if len(self._msg_timestamps) >= self.config.SEND_RATE_LIMIT:
                self.LOG.warning("发送消息过快，已达到每分钟" + self.config.SEND_RATE_LIMIT + "条上限。")
                return
            self._msg_timestamps.append(now)

        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                wxids = at_list.split(",")
                for wxid in wxids:
                    # 根据 wxid 查找群昵称
                    ats += f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三
        if ats == "":
            self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"To {receiver}: {ats}\r{msg}")
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

    def getAllContacts(self) -> dict:
        """
        获取联系人（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in contacts}

    def keepRunningAndBlockProcess(self) -> None:
        """
        保持机器人运行，不让进程退出
        """
        while True:
            self.runPendingJobs()
            time.sleep(1)

    def autoAcceptFriendRequest(self, msg: WxMsg) -> None:
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            self.wcf.accept_new_friend(v3, v4, scene)

        except Exception as e:
            self.LOG.error(f"同意好友出错：{e}")

    def sayHiToNewFriend(self, msg: WxMsg) -> None:
        nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
        if nickName:
            # 添加了好友，更新好友列表
            self.allContacts[msg.sender] = nickName[0]
            self.sendTextMsg(f"Hi {nickName[0]}，我自动通过了你的好友请求。", msg.sender)

    def newsReport(self) -> None:
        receivers = self.config.NEWS
        if not receivers:
            return

        news = News().get_important_news()
        for r in receivers:
            self.sendTextMsg(news, r)

    def weatherReport(self) -> None:
        receivers = self.config.WEATHER
        if not receivers or not self.config.CITY_CODE:
            self.LOG.warning("未配置天气城市代码或接收人")
            return

        report = Weather(self.config.CITY_CODE).get_weather()
        for r in receivers:
            self.sendTextMsg(report, r)
