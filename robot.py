# -*- coding: utf-8 -*-
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from functools import wraps
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
import db

__version__ = "39.2.4.0"


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
        self.BOT_FUNC = {
            '#菜单': self.botMenu,
            '#转发': self.botForward,
            '#新闻': self.newsReport,
            "#成语": "",
            "？成语": "",
            "#当前成语": "",
            "#重置成语": "",

        }

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

    # 机器人指令识别
    def is_bot_command(func):
        """装饰器判断消息是否为机器人指令，执行相应的操作"""

        @wraps(func)
        def wrapper(self, msg):
            texts = re.findall(r"^([#?？!！%])([\s\S]*)$", msg.content)
            # print(f"texts:{texts}")
            if texts:
                flag, text = texts[0]  # 拆分符号和文本内容
                matches = re.findall(r"^(转发)([\s\S]*)$", text)
                commends, content = matches[0] if matches else (None, None)

                if flag == "#":
                    if text == "菜单":
                        # print("菜单函数")
                        self.botMenu(msg)
                    elif text == "新闻":
                        # print("新闻函数")
                        self.newsReport(msg)
                        db.update_user_points(msg.sender, -1)
                    elif commends == "转发" and content:
                        # print("转发函数")
                        self.botForward(msg)
                    elif text == "积分":
                        self.get_wx_points(msg)

                    elif text == "类型":
                        self.get_all_type_msg()
                    elif text=="friendList":
                        self.get_friend_info()
                    return  # 直接跳过，不执行原函数

            # 如果没有命中指令，执行原函数
            return func(self, msg)

        return wrapper

    def is_chengyu_command(func):
        """装饰器判断消息是否为成语相关指令，执行相应的操作"""

        @wraps(func)
        def wrapper(self, msg):
            # 匹配以#开头的成语指令
            texts = re.findall(r"^([#?？])(.*)$", msg.content)
            if texts:
                flag, text = texts[0]  # 拆分符号和文本内容  # 获取用户的微信ID
                # 处理不同的成语相关指令
                if flag == "#":
                    if cy.isChengyu(text):
                        status, res = cy.getNext(msg.sender, text)
                        if status:
                            res += "\n积分+2"
                            self.sendTextMsg(res, msg.roomid, msg.sender)
                            db.update_user_points(msg.sender, 2)
                            return
                        else:
                            self.sendTextMsg(res, msg.roomid, msg.sender)
                            return
                    elif flag in ["?", "？"]:  # 查词
                        if cy.isChengyu(text):
                            rsp = cy.getMeaning(text)
                            if rsp:
                                self.sendTextMsg(rsp, msg.roomid, msg.sender)
                                return
                    elif text == "当前成语":
                        # 查询当前成语
                        self.sendTextMsg(cy.query_current_chengyu(msg.sender), msg.roomid, msg.sender)
                        return
                    elif text == "重置成语":
                        # 重置成语
                        self.sendTextMsg(cy.reset_current_chengyu(msg.sender), msg.roomid, msg.sender)
                        return
                elif flag in ["?", "？"]:
                    # 查询成语的意义
                    self.sendTextMsg(cy.getMeaning(text), msg.roomid, msg.sender)
                    return
            return func(self, msg)  # 如果不是成语指令，执行原函数

        return wrapper

    def get_wx_points(self, msg: WxMsg):
        points = db.get_points(msg.sender)
        if msg.from_group():
            res = f"你当前的积分为：{points}"
            self.sendTextMsg(res, msg.roomid, msg.sender)
        else:
            res = f'你的当前积分为 {points}'
            self.sendTextMsg(res, msg.sender)
        return True

    def botForward(self, msg: WxMsg) -> None:
        """
        转发消息
        @param msg:
        @return: None
        """
        if msg.sender not in self.config.ROOTIDS:
            return
        try:
            for i in self.config.BOT_TEXT_FORWARD:
                self.sendTextMsg(msg.content, i)
        except Exception as e:
            self.LOG.error(f"转发函数内部：{e}")
            return

    def botMenu(self, msg: WxMsg) -> bool:
        """
        return: 返回机器人菜单
        """
        menu = "\n".join(self.BOT_FUNC.keys())
        if menu:
            if msg.from_group():
                self.sendTextMsg(menu, msg.roomid)
            else:
                self.sendTextMsg(menu, msg.sender)
            return True
        return False

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        db.get_or_create_user_by_wechat_id(msg.sender)
        return self.toChitchat(msg)

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT
        """
        if not self.chat:  # 没接 ChatGPT，固定回复
            rsp = "你@我干嘛？"

        else:  # 接了 ChatGPT，智能回复
            points = db.get_points(msg.sender)
            if points < 1:
                rsp = "积分不足！"
                if msg.from_group():

                    self.sendTextMsg(rsp, msg.roomid, msg.sender)
                    return False
                else:
                    self.sendTextMsg(rsp, msg.sender)
                    return False
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            rsp = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))

        if rsp:
            if msg.from_group():
                self.sendTextMsg(rsp, msg.roomid, msg.sender)
            else:
                self.sendTextMsg(rsp, msg.sender)
            db.update_user_points(msg.sender, -1)
            return True
        else:
            self.LOG.error(f"无法从 ChatGPT 获得答案")
            return False

    @is_chengyu_command
    @is_bot_command
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

            return  # 处理完群聊信息，后面就不需要处理了

        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)

        elif msg.type == 10000:
            code = self.wcf.send_pat_msg(msg.roomid, msg.sender)
            # 系统信息
            self.sayHiToNewFriend(msg)
        elif msg.type == 922746929:
            self.LOG.info("执行拍一拍类型")
            code = self.wcf.send_pat_msg(msg.roomid, msg.sender)
            self.LOG.info(code)
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
            # print(msg.type)
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
                    # 信息打印
                    # self.LOG.info(msg)
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
            # self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            # self.LOG.info(f"To {receiver}: {ats}\r{msg}")
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
        self.LOG.debug("开始处理好友申请")
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

    def newsReport(self, msg: WxMsg) -> None:
        # receivers = self.config.NEWS
        # if not receivers:
        #     return

        news = News().get_important_news()
        # for r in receivers:
        if msg.from_group():
            self.sendTextMsg(news, msg.roomid)
        else:
            self.sendTextMsg(news, msg.sender)

    def get_all_type_msg(self) -> dict:
        """
        获取所有消息类型并将其保存到outtype.json中
        """
        # 获取消息类型字典
        msg_types = self.wcf.get_msg_types()

        # 保存到 outtype.json 文件中
        with open('outtype.json', 'w', encoding='utf-8') as file:
            json.dump(msg_types, file, ensure_ascii=False, indent=4)

        # 返回获取到的字典
        return msg_types

    def weatherReport(self) -> None:
        receivers = self.config.WEATHER
        if not receivers or not self.config.CITY_CODE:
            self.LOG.warning("未配置天气城市代码或接收人")
            return

        report = Weather(self.config.CITY_CODE).get_weather()
        for r in receivers:
            self.sendTextMsg(report, r)

    def get_friend_info(self):
        """
        获取联系人并保存为json文件
        @return:
        """
        res = self.wcf.get_contacts()
        with open("friendsInfo.json", 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
