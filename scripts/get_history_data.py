import json
import sys
import time
from pathlib import Path
from pprint import pprint
from tkinter.tix import COLUMN
from typing import Dict, List, TypedDict

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
sys.path.append(str(ROOT))

from helper.lcu import LcuClient

COLUMNS = [
    "assists", "champLevel", "damageSelfMitigated", "deaths", "firstBloodKill",
    "goldEarned", "killingSprees", "kills", "largestMultiKill",
    "longestTimeSpentLiving", "pentaKills", "quadraKills", "totalDamageDealt",
    "totalDamageDealtToChampions", "totalDamageTaken", "totalHeal", "totalMinionsKilled",
    "tripleKills", "trueDamageDealt", "win"
]

class MemberMatches(TypedDict):
    summoner_id: int      # 玩家id
    matches: List[Dict] # 最近20场游戏数据


class MatchData(TypedDict):
    match_id: int
    creation: int
    win: bool                           # 本局比赛胜负（预测目标）
    members_data: List[MemberMatches]   # 己方队伍五位玩家的近20场游戏数据


def get_members(client: LcuClient, game_id: int, team_id: int) -> List[int]:
    """根据比赛id获取己方玩家id

    Args:
        client: LcuClient实例
        game_id: 比赛id
        team_id: 队伍id
    Returns:
        members: 己方玩家id列表
    """
    while True:
        detail = client.get_match_detail(str(game_id))
        if not detail.get("errorCode"):
            break
        time.sleep(0.5)
    member_id_start = 0 if team_id == 100 else 5
    return [
        member["player"]["summonerId"]
        for member in detail["participantIdentities"][member_id_start: member_id_start + 5]
    ]


def get_member_matches(client: LcuClient,
                       game_id: int,
                       game_creation: int,
                       start_idx: int,
                       summoner_id: int
                       ) -> MemberMatches:
    """获取指定队伍成员的近20场游戏数据

    Args:
        client: LcuClient实例
        game_id: 比赛id
        game_creation: 比赛创建时间
        start_idx: 获取比赛记录的起始位置
        summoner_id: 召唤师id
    Returns:
        match_data: 比赛数据
    """
    while True:
        if start_idx < 0:
            break
        count = 0
        while not (matches := client.get_match_history(summoner_id, start_idx)):
            count += 1
            if count >= 2:
                return MemberMatches(summoner_id=summoner_id, matches=[])
            time.sleep(0.5)

        if matches[-1]["gameCreation"] < game_creation:
            start_idx -= len(matches)
        elif matches[0]["gameCreation"] > game_creation:
            start_idx += len(matches)
        else:
            for match in reversed(matches):
                start_idx += 1
                if match["gameId"] == game_id:
                    break
            break
    matches = client.get_match_history(summoner_id, start_idx)

    _matches = []
    for match in matches:
        match_data = { 
            column : match["participants"][0]["stats"][column]
            for column in COLUMNS}
        match_data.update({"creation": match["gameCreation"],
                           "duration": match["gameDuration"],})
        _matches.append(match_data)

    return MemberMatches(
        summoner_id=summoner_id,
        matches=_matches)

def get_matches_data(client: LcuClient, nums: int = 0, filename: str = "") -> List[MatchData]:
    """获取指定场次的大乱斗比赛数据

    Args:
        client: LcuClient实例
        nums: 需要获取的场次数，默认获取全部比赛数据
        filename: 如果不为空则保存比赛记录到文件，文件均在data目录下，如果文件存在则返回文件数据
    Returns:
        matches_data: 比赛数据列表
    """
    _filename = DATA_DIR / filename
    if filename and _filename.is_file():
        with open(_filename, "r") as f:
            print(f"Loaded from file: {_filename}")
            return json.load(f)

    matches_data = []
    acquired_num = 0

    while len(matches_data) < nums or nums == 0:
        count = 0
        while not (
            matches := client.get_match_history(
                client.summoner_id, begin_index=len(matches_data))
            ):
            count += 1
            if count >= 2:
                break
            time.sleep(0.5)

        if not matches:
            print("\nNo more matches")
            break

        acquired_num += len(matches)

        for match in reversed(matches):
            if len(matches_data) >= nums and nums != 0:
                break
            if match["gameMode"] != "ARAM":
                continue
            summoner = match["participants"][0]
            members = get_members(client, match["gameId"], summoner["teamId"])
            matches_data.append(
                MatchData(
                    match_id=match["gameId"],
                    creation=match["gameCreation"],
                    win=summoner["stats"]["win"],
                    members_data=[
                        get_member_matches(
                            client,
                            match["gameId"],
                            match["gameCreation"],
                            acquired_num, member)
                        for member in members]
                )
            )
            print(f"Get match [{len(matches_data):4}/{nums}]: {match['gameId']}", end="\r")

    if filename:
        with open(_filename, 'w') as f:
            json.dump(matches_data, f)
        print(f"\rSave matches_data to file: {_filename}")

    return matches_data


def main():
    client = LcuClient()
    get_matches_data(client, 1000, "1000_matches_data.json")

if __name__ == '__main__':
    main()
