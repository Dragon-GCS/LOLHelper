import json

from tkinter import BooleanVar, Tk, Toplevel, ttk, Text
from threading import Thread
from typing import Callable

from loguru import logger
from . import config as CONF


def set_auto_confirm():
    CONF.AUTO_CONFIRM = not CONF.AUTO_CONFIRM
    logger.info("{}自动确认", "启动" if CONF.AUTO_CONFIRM else "关闭")


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
        # 需要自动选择的英雄与对应的滚动条
        self.selected = ttk.Treeview(self, show="tree")
        self.selected.grid(row=0, column=3, sticky="nsew", pady=2, padx=2)
        selected_bar = ttk.Scrollbar(
            self, orient="vertical", command=self.not_selected.yview)
        selected_bar.grid(row=0, column=4, sticky="ns")
        self.selected.configure(yscrollcommand=selected_bar.set)

        # 选择按钮
        button_frame = ttk.Frame(self)
        button_frame.grid(row=0, column=2, sticky="nsew", padx=5)
        button_frame.rowconfigure(0, weight=1)
        ttk.Button(button_frame, text="添加英雄",
                   command=self.add_champion).grid(row=1)
        ttk.Button(button_frame, text="删除英雄",
                   command=self.remove_champion).grid(row=2)
        button_frame.rowconfigure(3, weight=1)

        # 自动保存当前选择
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 显示英雄列表
        with open("champions.json", "r", encoding="utf8") as f:
            self.champions = json.load(f)
            self.champions["not-selected"] = dict(sorted(self.champions["not-selected"].items()))

        for champion_id, champion_name in self.champions["not-selected"].items():
            self.not_selected.insert(
                "", "end", text=champion_name, values=champion_id)

        for champion_id, champion_name in self.champions["selected"].items():
            self.selected.insert(
                "", "end", text=champion_name, values=champion_id)
            CONF.AUTO_PICKS.append(champion_id)

    def add_champion(self):
        # 将选择的英雄从未选择列表删除
        select = self.not_selected.focus()
        champion_id = self.not_selected.item(select)["values"][0]
        self.not_selected.delete(select)
        champion_name = self.champions["not-selected"].pop(str(champion_id))
        # 将选择的英雄添加到已选择列表
        self.selected.insert("", "end", text=champion_name, values=champion_id)
        self.champions["selected"][str(champion_id)] = champion_name
        CONF.AUTO_PICKS.append(champion_id)

    def remove_champion(self):
        # 将选择的英雄从已选择列表删除
        select = self.selected.focus()
        champion_id = self.selected.item(select)["values"][0]
        self.selected.delete(select)
        champion_name = self.champions["selected"].pop(str(champion_id))
        CONF.AUTO_PICKS.remove(champion_id)
        # 将选择的英雄添加到未选择列表首行
        temp = {str(champion_id): champion_name}
        temp.update(self.champions["not-selected"])
        self.champions["not-selected"] = temp
        self.not_selected.insert("", 0, text=champion_name, values=champion_id)

    def on_close(self):
        with open("champions.json", "w", encoding="utf8") as f:
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
        self.rowconfigure(1, weight=1)

        # 自动确认选项
        var = BooleanVar(value=CONF.AUTO_CONFIRM)
        ttk.Checkbutton(self,
                        text="自动确认",
                        command=set_auto_confirm,
                        variable=var
                        ).grid(row=0, column=0)

        # 设置英雄优先级
        ttk.Button(self, text="自动抢英雄", command=self.auto_pick).grid(
            row=0, column=1)

        # 启动按钮
        ttk.Button(self, text="启动助手", command=self.start).grid(row=0, column=2)

        # 日志框
        text = Text(self)
        text.grid(row=1, column=0, columnspan=4, sticky="nsew")

        # 滚动条
        vertical_bar = ttk.Scrollbar(
            self, orient="vertical", command=text.yview)
        vertical_bar.grid(row=1, column=5, sticky="ns")

        text.configure(yscrollcommand=vertical_bar.set)
        logger.add(lambda msg: text.insert("end", msg) or text.see("end"),
                   format="{message}")

    def start(self):
        if not self.start_flag:
            self.start_flag = True

            def with_callback():
                self.task()
                self.start_flag = False
            Thread(target=with_callback, daemon=True).start()
        else:
            logger.info("客户端监听已启动")

    def auto_pick(self):
        AutoPick(self).grab_set()
