# coding = utf-8
# Filename: api.py
# Dragon's Python3.8 code
# Created at 2022/05/27 10:06
# Edit with VS Code

import asyncio
import json
from typing import Coroutine, Optional, TypedDict, Union, cast

import psutil
from httpx import AsyncClient, HTTPStatusError
from loguru import logger

from . import config as CONF
from .algorithm import analysis_match_list
from .config import Route
from .exceptions import ClientNotStart, GameEnd, GameStart

_backgrounds = set()


def get_lcu_info() -> tuple[str, str]:
    """Get the lcu client token and port by process command line

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
    puuid: str  # 玩家id
    matches: list[dict]  # 最近20场游戏数据


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
        self.client = AsyncClient(base_url=self.base_url, verify=False)
        self.picked = False
        self.game_mode = ""
        self.members_matches: list[MemberMatches] = []
        self.champion_cache = {}
        self._tasks = set()

    def create_task(self, coro: Coroutine):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _request(self, method: str, api: str, **kwargs) -> dict:
        resp = await self.client.request(method, api, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    async def get(self, api: str) -> dict:
        return await self._request("GET", api)

    async def patch(self, api: str, data: Optional[dict] = None) -> dict:
        return await self._request("PATCH", api, json=data)

    async def post(self, api: str, data: Optional[dict] = None) -> dict:
        return await self._request("POST", api, json=data)

    async def send_message(self, session_id: str, message: str):
        """发送消息至指定会话"""

        logger.info("发送消息:\n{}", message)
        return await self.post(
            Route.ConversationMsg.format(conversationId=session_id),
            data={"body": message, "type": "chat"},
        )

    async def get_champion_name_by_id(self, champion_id: int) -> str:
        """根据英雄ID获取英雄名称"""
        if champion_id not in self.champion_cache:
            info = await self.get(Route.Champions.format(id=champion_id))
            self.champion_cache[champion_id] = f"{info['name']} {info['title']}"
        return self.champion_cache[champion_id]

    async def get_champion_select_session_id(self) -> str:
        """获取英雄选择界面对应聊天会话id"""

        for conversation in await self.get(Route.Conversations):
            if conversation["type"] == "championSelect":
                return conversation["id"]
        return ""

    async def get_current_game_mode(self) -> str:
        """获取当前游戏模式"""

        return (await self.get(Route.Session)).get("map", {}).get("gameMode", "")

    async def get_match_history(
        self, puuid: str, begin_index: int = 0, num: int = 20
    ) -> list[dict]:
        """获取指定召唤师的比赛记录，每次请求最多返回20条记录

        Args:
            begin_index: 请求记录的起始位置，从0开始
            num: 请求比赛记录的数量，最多返回20条记录
        Returns:
            returns: 比赛记录列表
        """
        resp = await self.get(
            Route.MatchList.format(puuid=puuid, begIdx=begin_index, endIdx=begin_index + num)
        )
        return resp.get("games", {}).get("games", [])

    async def get_match_detail(self, game_id: str) -> dict:
        """Game match detail by specified game id"""

        return await self.get(Route.MatchDetail.format(gameId=game_id))

    async def get_room_summoners_list(self, session_id: str) -> list[str]:
        """通过消息列表获取己方所有玩家的id"""

        summoners = []
        for _ in range(3):
            messages = await self.get(Route.ChatInfo.format(roomId=session_id))
            summoners = [
                msg["fromId"]
                for msg in messages
                if msg["body"] == "joined_room" and msg["type"] == "system"
            ]
            if len(summoners) >= 5:
                return summoners
            await asyncio.sleep(0.5)

        return summoners

    async def get_summoner_info(self):
        """获取当前登录的召唤师的基本信息"""

        summoner_info = await self.get(Route.CurrentSummoner)
        self.name = summoner_info["gameName"]
        self.puuid = summoner_info["puuid"]
        self.rolls = summoner_info["rerollPoints"]["numberOfRolls"]
        self.summoner_id = summoner_info["summonerId"]
        logger.info("当前召唤师: {}", self.name)

    async def accept_game(self):
        """接受游戏，发送请求至返回码为2xx"""

        while True:
            try:
                await self.post(Route.AcceptGame)
            except HTTPStatusError:
                await asyncio.sleep(1)
            else:
                break
        logger.info("对局已接受")

    async def calculate_summoner_score(self, puuid: str) -> tuple[MemberMatches, str]:
        """计算指定玩家的分数，返回玩家名称和分数，返回需要发送的消息和近20场游戏数据"""

        summoner_name = (await self.get(Route.Summoner.format(puuid=puuid)))["displayName"]
        matches = await self.get_match_history(puuid, 0)
        game_mode = await self.get_current_game_mode()
        kda, damage_per_minus, repeats, win_rate = analysis_match_list(matches, game_mode)
        message = (
            f"{summoner_name}战绩信息：\n"
            f"kda={kda:.2f}，分均伤害={damage_per_minus:.2f}\n"
            f"胜率={win_rate:2.0%}，{str(repeats) + '连胜' if repeats > 0 else str(-repeats) + '连败'}"
        )
        return MemberMatches(
            puuid=puuid,
            matches=[
                dict(
                    (
                        ("creation", match["gameCreation"]),
                        ("duration", match["gameDuration"]),
                        ("mode", match["gameMode"]),
                        *(
                            (k, v)
                            for k, v in match["participants"][0]["stats"].items()
                            if k in CONF.SAVE_ITEM
                        ),
                    )
                )
                for match in matches
            ],
        ), message

    async def analysis_summoners(self):
        """根据聊天信息获取己方所有召唤师，分析并计算己方的分数"""

        for _ in range(3):
            await asyncio.sleep(0.5)
            if session_id := await self.get_champion_select_session_id():
                break
        else:
            logger.error("Not found champion select session")
            return
        summoners = await self.get_room_summoners_list(session_id)
        logger.info("开始计算玩家分数: {}", summoners)

        for matches, msg in await asyncio.gather(
            *[self.calculate_summoner_score(puuid) for puuid in summoners]
        ):
            await asyncio.sleep(0.5)
            await self.send_message(session_id, msg)
            self.members_matches.append(matches)

        await self.send_message(session_id, "乱斗助手：github/Dragon-GCS/lolhelper")

    async def pick_champion(self, champion_id: int, session_info: dict):
        """选择英雄"""

        if self.picked:
            return

        if session_info["benchEnabled"]:
            if champion_id in session_info["benchChampionIds"]:
                await self.post(Route.SwapChampion.format(championId=champion_id))
                self.picked = True
                logger.info("自动选择英雄: {}", await self.get_champion_name_by_id(champion_id))
            return

        for actions in session_info.get("actions", []):
            for action in actions:
                if (
                    action["actorCellId"] == session_info["localPlayerCellId"]
                    and action["type"] == "pick"
                    and action["isInProgress"]
                ):
                    await self.patch(
                        Route.BpChampion.format(actionId=action["id"]),
                        data={"completed": True, "type": "pick", "championId": champion_id},
                    )
                    self.picked = True
                    logger.info("自动选择英雄: {}", await self.get_champion_name_by_id(champion_id))
                    return

    async def auto_pick(self, data: dict):
        """自动选择英雄"""
        for champion in CONF.AUTO_PICKS:
            champion = int(champion)
            for summoner in data["myTeam"]:
                if (
                    summoner["summonerId"] == self.summoner_id
                    and summoner["championId"] == champion
                ):
                    self.picked = True
                    return
            await self.pick_champion(champion, data)

    async def handle_ws_response(self, resp: Union[str, bytes]):
        """监听并处理Lcu客户端通过WebSocket发送的消息，并在切换GameFlow时进行处理"""

        if not resp:
            return

        content = json.loads(resp)

        if len(content) < 3 or not isinstance(content := content[2], dict):
            logger.exception("Invalid response: {}", content)
            return

        if not content["data"]:
            return

        if content["uri"] == Route.GameFlow:
            logger.info(f"切换客户端状态: {content['data']}")
            if content["data"] == "ChampSelect":
                self.picked = False
                logger.info("当前游戏模式: {}", await self.get_current_game_mode())
                self.create_task(self.analysis_summoners())

            if content["data"] == "ReadyCheck" and CONF.AUTO_CONFIRM:
                await self.accept_game()
            if content["data"] == "PreEndOfGame":
                raise GameEnd()
            if content["data"] == "InProgress":
                raise GameStart()
            if content["data"] == "GameStart" and CONF.SAVE_MATCH and self.members_matches:
                with CONF.MATCH_FILE.open("a") as f:
                    f.write(json.dumps(self.members_matches))
                    f.write("\n")
                self.members_matches = []

        if (
            not self.picked
            and content["uri"] == Route.BpSession
            and content["eventType"] == "Update"
            and CONF.AUTO_PICK_SWITCH
        ):
            await self.auto_pick(content["data"])  # type: ignore


if __name__ == "__main__":

    async def main():
        lcu = LcuClient()
        print(lcu.base_url)
        await lcu.get_summoner_info()
        print(await lcu.get_current_game_mode())
        print(await lcu.get_champion_select_session_id())
        print(await lcu.analysis_summoners())

    asyncio.run(main())
