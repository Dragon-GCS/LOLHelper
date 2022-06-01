# coding = utf-8
# Filename: api.py
# Dragon's Python3.8 code
# Created at 2022/05/27 10:06
# Edit with VS Code


from email import message
from multiprocessing.pool import ThreadPool
from pprint import pprint
from .algorithm import *
from .config import DEBUG, ROUTE
from .exceptions import *
from . import config as CONF
from requests import Response
from loguru import logger
from typing import Dict, List, Tuple
from websockets.typing import Data

import json
import requests
import psutil
import time
import warnings
warnings.filterwarnings("ignore")


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


class LcuClient:
    name: str
    puuid: str
    summoner_id: str
    rolls: int
    game_mode: str

    def __init__(self) -> None:
        token, port = get_lcu_info()
        if not token:
            raise ClientNotStart
        self.base_url = f"https://riot:{token}@127.0.0.1:{port}"
        self.get_summoner_info()

    def get(self, route: str) -> Response:
        return requests.get(self.base_url + route, verify=False)

    def patch(self, route: str, data: dict = {}) -> Response:
        return requests.patch(self.base_url + route, json=data, verify=False)

    def post(self, route: str, data: dict = {}) -> Response:
        return requests.post(self.base_url + route, json=data, verify=False)

    def send_message(self, session_id: str, message: str):
        """发送消息至指定会话"""

        logger.info("发送消息: {}", message)
        return self.post(
            ROUTE["conversation-msg"].format(conversationId=session_id),
            data={"body": message, "type": "chat"})

    def get_all_matches(self, summoner_id: str):
        """获取指定召唤师的所有比赛记录"""

        # items = ["gameId", "gameMode", "gameDuration",
        #          "gameCreation", "participants"]
        matches = []
        start_index = 0
        while True:
            result = self.get_match_history(summoner_id, start_index)
            matches = result + matches
            if not result:
                break
            logger.debug("Get matches: {}", len(matches))
            start_index += 20
            time.sleep(0.5)

        return matches

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
                          summoner_id: str,
                          begin_index: int,
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

    def get_room_summoners_list(self, session_id: str) -> List[str]:
        """获取己方所有玩家的id"""

        messages = []
        for _ in range(3):
            messages = self.get_messages(session_id)
            if len(messages) >= 5:
                break
            time.sleep(0.5)

        return [
            msg["fromSummonerId"]
            for msg in messages
            if msg["body"] == "joined_room" and msg["type"] == "system"
        ]

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
                logger.info("对局已ji")
                break
            time.sleep(1)

    def calculate_summoner_score(self, summoner_id: str) -> Tuple[str, int]:
        """计算指定玩家的分数，返回玩家名称和分数"""

        summoner_name = self.get(ROUTE["summoner"].format(
            summonerId=summoner_id)).json()["displayName"]
        matches = self.get_match_history(summoner_id, 0)
        bonus = calculate_wining_bonus(matches)
        logger.info("{} {}", summoner_name, 0)
        # self.send_message(session_id, f"{name} {score}")
        return summoner_name, 0

    def analysis_summoners(self):
        """分析并计算当前己方所有玩家的分数"""

        for _ in range(3):
            time.sleep(0.5)
            if session_id := self.get_champion_select_session_id():
                break
        else:
            logger.error("Not found champion select session")
            return

        summoners = self.get_room_summoners_list(session_id)
        print(summoners)
        logger.info("开始计算玩家分数")
        with ThreadPool(len(summoners)) as pool:
            pool.map_async(self.calculate_summoner_score, summoners)

    def pick_champion(self, champion_id: int):
        """选择英雄"""

        if self.get_current_game_mode() == "ARAM":
            self.post(ROUTE["swap-champion"].format(championId=champion_id))
            return

        session_info = self.get(ROUTE["BpSession"]).json()
        if not session_info.get("actions", []):
            return

        for actions in session_info["actions"]:
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
                    return

    def handle_ws_response(self, resp: Data):
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
                CONF.DEBUG = True
                logger.info("当前游戏模式: {}", self.get_current_game_mode())
                self.analysis_summoners()
            if content["data"] == "ReadyCheck" and CONF.AUTO_CONFIRM:
                self.accept_game()
            if content["data"] == "PreEndOfGame":
                raise GameEnd()
            if content["data"] == "InProgress":
                raise GameStart()

        # if content["uri"] == ROUTE["current-champion"]:
        #     logger.info(
        #         "当前英雄：{}", self.get_champion_name_by_id(content["data"]))

        if CONF.DEBUG and content["uri"] == ROUTE["ChampionBench"]:
            for champions in CONF.AUTO_PICKS:
                if champions in content["data"]["benchChampionIds"]:
                    self.pick_champion(champions)



if __name__ == '__main__':
    lcu = LcuClient()
    print(lcu.get_match_history(lcu.summoner_id, 0, 1))
