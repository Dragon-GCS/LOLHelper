# coding = utf-8
# Filename: api.py
# Dragon's Python3.8 code
# Created at 2022/05/27 10:06
# Edit with VS Code

import json
import requests
import psutil
import time
import warnings
warnings.filterwarnings("ignore")

from multiprocessing.pool import ThreadPool
from pprint import pprint
from threading import Thread
from typing import Dict, List, Tuple, TypedDict, Union

from loguru import logger
from requests import Response

from .algorithm import analysis_match_list
from .config import ROUTE
from .exceptions import *
from . import config as CONF


def get_lcu_info() -> Tuple[str, str]:
    """Get the lcu client token and prot by process command line

    Returns:
        token: token for lcu api
        port: port for lcu api
    """
    cmdline, token, port = [], "", ""
    for proc in psutil.process_iter():
        if proc.name() == CONF.PROCESS_NAME:
            cmdline = proc.cmdline()
            break

    for args in cmdline:
        if args.startswith("--remoting-auth-token"):
            token = args.split("=")[1]
        if args.startswith("--app-port"):
            port = args.split("=")[1]

    logger.info(f"当前客户端信息: token={token}, port={port}")
    return token, port


class MemberMatches(TypedDict):
    summoner_id: int      # 玩家id
    matches: List[Dict] # 最近20场游戏数据


class LcuClient:
    name: str
    puuid: str
    summoner_id: int
    rolls: int

    def __init__(self):
        token, port = get_lcu_info()
        if not token:
            raise ClientNotStart
        self.base_url = f"https://riot:{token}@127.0.0.1:{port}"
        self.get_summoner_info()
        self.picked = False
        self.game_mode = ""
        self.members_matches: List[MemberMatches] = []

    def get(self, route: str) -> Response:
        return requests.get(self.base_url + route, verify=False)

    def patch(self, route: str, data: dict = {}) -> Response:
        return requests.patch(self.base_url + route, json=data, verify=False)

    def post(self, route: str, data: dict = {}) -> Response:
        return requests.post(self.base_url + route, json=data, verify=False)

    def send_message(self, session_id: str, message: str):
        """发送消息至指定会话"""

        logger.info("发送消息:\n{}", message)
        return self.post(
            ROUTE["conversation-msg"].format(conversationId=session_id),
            data={"body": message, "type": "chat"})

    def get_champion_name_by_id(self, champion_id: int) -> str:
        """根据英雄ID获取英雄名称"""

        info = self.get(ROUTE["champions"].format(id=champion_id)).json()
        return f'{info["name"]} {info["title"]}'

    def get_champion_select_session_id(self) -> str:
        """获取英雄选择界面对应聊天会话id"""

        for conversation in self.get(ROUTE["conversations"]).json():
            if conversation["type"] == "championSelect":
                return conversation["id"]
        return ""

    def get_current_game_mode(self) -> str:
        """获取当前游戏模式"""

        return self.get(
            ROUTE["session"]
        ).json().get("map", {}).get("gameMode", "")

    def get_match_history(self,
                          summoner_id: int,
                          begin_index: int = 0,
                          num: int = 20
                          ) -> List[dict]:
        """获取指定召唤师的比赛记录，每次请求最多返回20条记录

        Args:
            begin_index: 请求记录的起始位置，从0开始
            num: 请求比赛记录的数量，最多返回20条记录
        Returns:
            returns: 比赛记录列表
        """
        return self.get(
            ROUTE["match-list"].format(
                summonerId=summoner_id,
                begIdx=begin_index,
                endIdx=begin_index + num)
        ).json().get("games", {}).get("games", [])

    def get_match_detail(self, game_id: str) -> dict:
        """Game match detail by specified game id"""

        return self.get(ROUTE["match-detail"].format(gameId=game_id)).json()

    def get_messages(self, session_id: str) -> List[dict]:
        """获取指定会话的所有消息"""

        return self.get(ROUTE["conversation-msg"].format(conversationId=session_id)).json()

    def get_room_summoners_list(self, session_id: str) -> List[int]:
        """获取己方所有玩家的id"""

        messages = []
        for _ in range(3):
            messages = [msg["fromSummonerId"]
                        for msg in self.get_messages(session_id)
                        if msg["body"] == "joined_room" and msg["type"] == "system"]
            if len(messages) >= 5:
                return messages
            time.sleep(0.5)

        return messages

    def get_summoner_info(self):
        """获取当前登录的召唤师的基本信息"""

        summoner_info = self.get(ROUTE["current-summoner"]).json()
        self.name = summoner_info["displayName"]
        self.puuid = summoner_info["puuid"]
        self.rolls = summoner_info["rerollPoints"]["numberOfRolls"]
        self.summoner_id = summoner_info["summonerId"]
        logger.info("当前召唤师: {}", self.name)

    def accept_game(self):
        """接受游戏，发送请求至返回码为2xx"""

        while True:
            resp = self.post(ROUTE["accept-game"])
            if str(resp.status_code).startswith("2"):
                logger.info("对局已接受")
                break
            time.sleep(1)

    def calculate_summoner_score(self, summoner_id: int) -> Tuple[MemberMatches, str]:
        """计算指定玩家的分数，返回玩家名称和分数，返回需要发送的消息和近20场游戏数据"""

        summoner_name = self.get(ROUTE["summoner"].format(
            summonerId=summoner_id)).json()["displayName"]
        matches = self.get_match_history(summoner_id, 0)
        game_mode = self.get_current_game_mode()
        kda, damage_per_minus, repeats, win_rate = analysis_match_list(matches, game_mode)
        message = f"{summoner_name}战绩信息：\n"\
                  f"kda={kda:.2f}，分均伤害={damage_per_minus:.2f}\n"\
                  f"胜率={win_rate:2.0%}，{str(repeats) + '连胜' if repeats > 0 else str(-repeats) + '连败'}"
        return MemberMatches(
            summoner_id=summoner_id,
            matches=[dict((
                ("creation", match["gameCreation"]),
                ("duration", match["gameDuration"]),
                ("mode", match["gameMode"]),
                *((k, v) for k,v in match["participants"][0]["stats"].items()
                   if k in CONF.SAVE_ITEM)
                ))
                for match in matches]
            ), message

    def analysis_summoners(self):
        """根据聊天信息获取己方所有召唤师，分析并计算己方的分数"""

        for _ in range(3):
            time.sleep(0.5)
            if session_id := self.get_champion_select_session_id():
                break
        else:
            logger.error("Not found champion select session")
            return
        summoners = self.get_room_summoners_list(session_id)
        logger.info("开始计算玩家分数: {}", summoners)

        with ThreadPool(5) as pool:
            for matches, msg in pool.imap(self.calculate_summoner_score, summoners):
                time.sleep(0.5) # 防止晚进入房间的玩家看不到信息
                self.send_message(session_id, msg)
                self.members_matches.append(matches)
        self.send_message(session_id, "乱斗助手下载地址：gitee上搜lolhelper。作者Dragon-GCS")

    def pick_champion(self, champion_id: int, session_info: dict):
        """选择英雄"""

        # session_info = self.get(ROUTE["BpSession"]).json()
        if self.picked:
            return

        if session_info["benchEnabled"]:
            if champion_id in session_info["benchChampionIds"]:
                self.post(
                    ROUTE["swap-champion"].format(championId=champion_id))
                self.picked = True
                logger.info(
                    "自动选择英雄: {}", self.get_champion_name_by_id(champion_id))
            return

        for actions in session_info.get("actions", []):
            for action in actions:
                if action["actorCellId"] == session_info["localPlayerCellId"] \
                        and action['type'] == 'pick' \
                        and action['isInProgress']:
                    self.patch(
                        ROUTE["bp-champion"].format(actionId=action["id"]),
                        data={
                            "completed": True,
                            "type": "pick",
                            "championId": champion_id
                        }
                    )
                    self.picked = True
                    logger.info(
                        "自动选择英雄: {}", self.get_champion_name_by_id(champion_id))
                    return

    def auto_pick(self, data: Dict):
        """自动选择英雄"""
        for champion in CONF.AUTO_PICKS:
            champion = int(champion)
            for summoner in data["myTeam"]:
                if summoner["summonerId"] == self.summoner_id and summoner["championId"] == champion:
                    self.picked = True
                    return
            self.pick_champion(champion, data)

    def handle_ws_response(self, resp: Union[str, bytes]):
        """监听并处理Lcu客户端通过WebSocket发送的消息，并在切换GameFlow时进行处理"""

        if not resp:
            return

        content = json.loads(resp)

        if len(content) < 3 or type(content := content[2]) != dict:
            logger.exception("Invalid response: {}", content)
            return

        if not content["data"]:
            return

        if content["uri"] == ROUTE["GameFlow"]:
            logger.info(f"切换客户端状态: {content['data']}")
            if content["data"] == "ChampSelect":
                self.picked = False
                logger.info("当前游戏模式: {}", self.get_current_game_mode())
                if CONF.AUTO_ANALYSIS:
                    Thread(target=self.analysis_summoners).start()
            if content["data"] == "ReadyCheck" and CONF.AUTO_CONFIRM:
                self.accept_game()
            if content["data"] == "PreEndOfGame":
                raise GameEnd()
            if content["data"] == "InProgress":
                raise GameStart()
            if content["data"] == "GameStart" and CONF.SAVE_MATCH and self.members_matches:
                with open(CONF.MATCH_FILE, "a") as f:
                    f.write(json.dumps(self.members_matches))
                    f.write("\n")
                self.members_matches = []

        # if content["uri"] == ROUTE["current-champion"]:
        #     logger.info(
        #         "当前英雄：{}", self.get_champion_name_by_id(content["data"]))

        if not self.picked and content["uri"] == ROUTE["BpSession"] \
            and CONF.AUTO_PICK_SWITCH:
            self.auto_pick(content["data"])


if __name__ == '__main__':
    lcu = LcuClient()
    print(lcu.get_match_history(lcu.summoner_id, 0, 1))
