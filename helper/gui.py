import json

from tkinter import BooleanVar, Tk, Toplevel, ttk, Text
from threading import Thread
from typing import Callable

from helper.exceptions import ClientNotStart
from helper.lcu import LcuClient

from loguru import logger
from . import config as CONF


def set_auto_analysis():
    CONF.AUTO_ANALYSIS = not CONF.AUTO_ANALYSIS
    logger.info("战绩分析：{}", "开启" if CONF.AUTO_ANALYSIS else "关闭")


def set_auto_confirm():
    CONF.AUTO_CONFIRM = not CONF.AUTO_CONFIRM
    logger.info("自动确认：{}", "开启" if CONF.AUTO_CONFIRM else "关闭")

def set_auto_pick():
    CONF.AUTO_PICK_SWITCH = not CONF.AUTO_PICK_SWITCH
    logger.info("自动选择：{}", "开启" if CONF.AUTO_PICK_SWITCH else "关闭")

def set_save_match():
    CONF.SAVE_MATCH = not CONF.SAVE_MATCH
    logger.info("保存队友最近20场比赛记录：{}", "开启" if CONF.SAVE_MATCH else "关闭")


class AutoPick(Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("自动选择英雄")
        self.geometry("480x480")
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)
        self.rowconfigure(0, weight=1)

        # 不需要自动选择的英雄与对应的滚动条
        self.not_selected = ttk.Treeview(self, show="tree")
        self.not_selected.grid(row=0, column=1, sticky="nsew", pady=2, padx=2)
        not_select_bar = ttk.Scrollbar(
            self, orient="vertical", command=self.not_selected.yview)
        not_select_bar.grid(row=0, column=0, sticky="ns")
        self.not_selected.configure(yscrollcommand=not_select_bar.set)
        self.not_selected.bind("<Double-1>", lambda _: self.add_champion())
        # 需要自动选择的英雄与对应的滚动条
        self.selected = ttk.Treeview(self, show="tree")
        self.selected.grid(row=0, column=3, sticky="nsew", pady=2, padx=2)
        selected_bar = ttk.Scrollbar(
            self, orient="vertical", command=self.not_selected.yview)
        selected_bar.grid(row=0, column=4, sticky="ns")
        self.selected.configure(yscrollcommand=selected_bar.set)
        self.selected.bind("<Double-1>", lambda _: self.remove_champion())

        # 选择按钮
        button_frame = ttk.Frame(self)
        button_frame.grid(row=0, column=2, sticky="nsew", padx=5)
        button_frame.rowconfigure(0, weight=1)
        ttk.Button(button_frame, text="添加英雄>>",
                   command=self.add_champion).grid(row=1)
        ttk.Button(button_frame, text="<<删除英雄",
                   command=self.remove_champion).grid(row=2)
        ttk.Button(button_frame, text="向上移动↑↑",
                   command=self.move_up).grid(row=3)
        ttk.Button(button_frame, text="向下移动↓↓",
                   command=self.move_down).grid(row=4)
        button_frame.rowconfigure(5, weight=1)

        # 自动保存当前选择
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 第一次使用加载英雄列表
        if not CONF.AUTO_PICK_CACHE.exists():
            logger.info("未找到英雄列表文件，正在下载...")
            client = LcuClient()
            self.champions = {
                "not-selected": {
                    str(champion["id"]): f"{champion['name']} {champion['title']}"
                    for champion in client.get(CONF.ROUTE["all-champions"]).json()},
                "selected": {},
            }
            with open(CONF.AUTO_PICK_CACHE, "w", encoding="utf8") as f:
                json.dump(self.champions, f, ensure_ascii=False)
        else:
            # 显示英雄列表
            with open(CONF.AUTO_PICK_CACHE, "r", encoding="utf8") as f:
                self.champions = json.load(f)
                self.champions["not-selected"] = dict(
                    sorted(self.champions["not-selected"].items(), key=lambda x: int(x[0])))

        for champion_id, champion_name in self.champions["not-selected"].items():
            self.not_selected.insert(
                "", "end", text=champion_name, values=champion_id)

        for champion_id, champion_name in self.champions["selected"].items():
            self.selected.insert(
                "", "end", text=champion_name, values=champion_id)
        CONF.AUTO_PICKS = list(self.champions["selected"])

    def add_champion(self):
        """将未选择的英雄从列表添加至已选择列表结尾"""

        select = self.not_selected.focus()
        champion_id = str(self.not_selected.item(select)["values"][0])
        self.not_selected.delete(select)
        champion_name = self.champions["not-selected"].pop(champion_id)

        self.selected.insert("", "end", text=champion_name,
                             values=(champion_id,))
        self.champions["selected"][champion_id] = champion_name
        CONF.AUTO_PICKS.append(champion_id)

    def remove_champion(self):
        """将已选择的英雄从列表删除并添加至未选择列表开头"""

        select = self.selected.focus()
        champion_id = str(self.selected.item(select)["values"][0])
        self.selected.delete(select)
        champion_name = self.champions["selected"].pop(champion_id)
        CONF.AUTO_PICKS.remove(champion_id)

        temp = {str(champion_id): champion_name}
        temp.update(self.champions["not-selected"])
        self.champions["not-selected"] = temp
        self.not_selected.insert(
            "", 0, text=champion_name, values=(champion_id,))

    def move_up(self):
        """将已选择的英雄向上移动"""
        select = self.selected.focus()
        idx = self.selected.index(select)
        self.selected.move(select, "", idx - 1)
        if idx > 0:
            CONF.AUTO_PICKS.insert(idx - 1, CONF.AUTO_PICKS.pop(idx))

    def move_down(self):
        """将已选择的英雄向下移动"""
        select = self.selected.focus()
        idx = self.selected.index(select)
        self.selected.move(select, "", idx + 1)
        if idx < len(CONF.AUTO_PICKS) - 1:
            CONF.AUTO_PICKS.insert(idx + 1, CONF.AUTO_PICKS.pop(idx))

    def on_close(self):
        self.champions["selected"] = {
            str(champion_id): self.champions["selected"][champion_id]
            for champion_id in CONF.AUTO_PICKS
        }
        with open(CONF.AUTO_PICK_CACHE, "w", encoding="utf8") as f:
            json.dump(self.champions, f, ensure_ascii=False)
        self.destroy()


class UI(Tk):
    def __init__(self, task: Callable):
        super().__init__()
        self.title("LOL大乱斗助手")
        self.geometry("480x480")
        self.task = task
        self.start_flag = False
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(2, weight=1)

        # 自动确认开关
        auto_pick_var = BooleanVar(value=CONF.AUTO_CONFIRM)
        ttk.Checkbutton(self,
                        text="自动确认",
                        command=set_auto_confirm,
                        variable=auto_pick_var
                        ).grid(row=0, column=0, sticky="we")

        # 自动选择英雄开关
        auto_pick_var = BooleanVar(value=CONF.AUTO_PICK_SWITCH)
        ttk.Checkbutton(self,
                        text="自动选英雄",
                        command=set_auto_pick,
                        variable=auto_pick_var
                        ).grid(row=0, column=1, sticky="we")

        # 自动分析开关
        auto_analysis_var = BooleanVar(value=CONF.AUTO_ANALYSIS)
        ttk.Checkbutton(self,
                        text="战绩分析",
                        command=set_auto_analysis,
                        variable=auto_analysis_var
                        ).grid(row=1, column=0, sticky="we")

        # 保存队友最近20场比赛记录
        save_match_var = BooleanVar(value=CONF.SAVE_MATCH)
        ttk.Checkbutton(self,
                        text="保存队友记录",
                        command=set_save_match,
                        variable=save_match_var
                        ).grid(row=1, column=1, sticky="we")

        # 设置英雄优先级
        ttk.Button(
            self, text="英雄优先级设置", command=self.auto_pick
            ).grid(row=0, column=2, sticky="we")

        # 启动按钮
        ttk.Button(
            self, text="启动助手", command=self.start).grid(row=1, column=2, sticky="we")

        # 日志框
        text = Text(self)
        text.grid(row=2, column=0, columnspan=3, sticky="nsew")

        # 滚动条
        vertical_bar = ttk.Scrollbar(
            self, orient="vertical", command=text.yview)
        vertical_bar.grid(row=2, column=3, sticky="ns")

        text.configure(yscrollcommand=vertical_bar.set)
        logger.add(lambda msg: text.insert("end", msg) or text.see("end"),
                   format="{time:HH:mm:ss} {message}")
        logger.info("自动确认：{}", "开启" if CONF.AUTO_CONFIRM else "关闭")
        logger.info("自动选人：{}", "开启" if CONF.AUTO_PICKS else "关闭")
        logger.info("战绩分析：{}", "开启" if CONF.AUTO_ANALYSIS else "关闭")
        logger.info("保存队友记录：{}", "开启" if CONF.SAVE_MATCH else "关闭")

    def start(self):
        if not self.start_flag:
            def with_callback():
                self.start_flag = True
                try:
                    self.task()
                except ClientNotStart:
                    logger.info("客户端未启动")
                logger.info("客户端监听已停止")
                self.start_flag = False
            Thread(target=with_callback, daemon=True).start()
        else:
            logger.info("客户端监听已启动")

    def auto_pick(self):
        AutoPick(self).grab_set()
