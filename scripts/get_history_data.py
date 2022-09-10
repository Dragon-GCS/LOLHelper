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


def load_matches_data(filename: str) -> List[MatchData]:
    _filename = DATA_DIR / filename
    if not _filename.is_file():
        print(f"File {_filename} not found")
        exit()

    with open(_filename, "r") as f:
        data = json.load(f)
        print(f"Load matches_data from {_filename}")
        return data


def save_matches_data(filename: str, data: List[MatchData]):
    _filename = DATA_DIR / filename
    with open(_filename, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False)
        print(f"Save matches_data to {_filename}")


def bin_search(matches, game_creation: int) -> int:
    """查找指定比赛记录在列表中的位置，列表中比赛按时间顺序排列

    Args:
        matches: 比赛记录列表
        game_id: 目标比赛id
    Returns:
        index: 目标游戏在列表中的位置
    """
    start = 0
    end = len(matches) - 1
    while start <= end:
        mid = (start + end) // 2
        if matches[mid]["gameCreation"] == game_creation:
            return len(matches) - mid 
        elif matches[mid]["gameCreation"] > game_creation:
            end = mid - 1
        else:
            start = mid + 1
        mid = (start + end) // 2
    return 10


class MatchGetter(LcuClient):
    def get_members(self, game_id: int, team_id: int) -> List[int]:
        """根据比赛id获取己方玩家id

        Args:
            game_id: 比赛id
            team_id: 队伍id
        Returns:
            members: 己方玩家id列表
        """
        while True:
            detail = self.get_match_detail(str(game_id))
            if not detail.get("errorCode"):
                break
            time.sleep(0.5)
        member_id_start = 0 if team_id == 100 else 5
        return [
            member["player"]["summonerId"]
            for member in detail["participantIdentities"][member_id_start: member_id_start + 5]
        ]


    def get_matches_list(self,
                        start_idx: int = 0,
                        nums: int = 0,
                        filename: str = ""
                        ) -> List[MatchData]:
        """获取指定场次的大乱斗比赛数据

        Args:
            start_idx: 获取比赛记录的起始位置
            nums: 需要获取的场次数，默认(0)获取全部比赛数据
            filename: 如果不为空则保存比赛记录到文件，文件均在data目录下，如果文件存在则返回文件数据
        Returns:
            matches_data: 比赛数据列表
        """
        print("Start get matches data")
        if filename and (DATA_DIR / filename).is_file():
            return load_matches_data(filename)

        matches_data = []
        end = start_idx + nums
        while start_idx < end or nums == 0:
            count = 0
            while not (
                matches := self.get_match_history(
                    self.summoner_id, begin_index=start_idx)
                ):
                count += 1
                if count >= 3:
                    break
                time.sleep(0.5)

            if not matches:
                print("\nNo more matches")
                break

            start_idx += len(matches)

            for match in reversed(matches):
                if len(matches_data) >= nums and nums != 0:
                    break
                if match["gameMode"] != "ARAM":
                    continue
                summoner = match["participants"][0]
                members = self.get_members(match["gameId"], summoner["teamId"])
                matches_data.append(
                    MatchData(
                        match_id=match["gameId"],
                        creation=match["gameCreation"],
                        win=summoner["stats"]["win"],
                        members_data=[
                            # get_member_matches(
                            #     client,
                            #     match["gameId"],
                            #     match["gameCreation"],
                            #     acquired_num, member)
                            MemberMatches(summoner_id=member, matches=[])
                            for member in members]
                    )
                )
                print(f"Get match [{len(matches_data):4}/{start_idx}/{end}]: {match['gameId']}", end="\r")
        print(f"\nTotal get{len(matches_data):4}/{start_idx}/{end}")

        if filename:
            save_matches_data(filename, matches_data)

        return matches_data



    def get_matches_detail(self, matches_data: List[MatchData] = [], filename: str = "") -> List[MatchData]:
        """读取比赛记录列表，获取己方队伍成员比赛前20场的数据

        Args:
            filename: 比赛记录文件名
        Returns:
            matches_detail: description
        """
        print("Start get matches detail")
        if filename and not matches_data:
            matches_data = load_matches_data(filename)

        for i, match in enumerate(matches_data):
            print(f"Getting match [{i + 1}/{len(matches_data)}] ...", end="\r")

            if len([member["matches"] for member in match["members_data"] if member["matches"]]) == 5:
                continue

            try:
                for i, member in enumerate(match["members_data"]):
                    if not member["matches"]:
                        match["members_data"][i] = self.get_member_matches(
                            game_creation=match["creation"],
                            start_idx=i,
                            summoner_id=member["summoner_id"]
                        )
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt, exit")
                break
            except Exception as e:
                print(e)

        save_matches_data(filename, matches_data)
        return matches_data


    def get_member_matches(self,
                           game_creation: int,
                           start_idx: int,
                           summoner_id: int
                           ) -> MemberMatches:
        """读取比赛记录文件，获取指定队伍成员的近20场游戏数据

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
            while not (matches := self.get_match_history(summoner_id, start_idx)):
                count += 1
                if count >= 3:
                    return MemberMatches(summoner_id=summoner_id, matches=[])
                time.sleep(0.5)

            if matches[-1]["gameCreation"] < game_creation:
                start_idx -= len(matches)
            elif matches[0]["gameCreation"] > game_creation:
                start_idx += len(matches)
            else:
                start_idx += bin_search(matches, game_creation)
                break

        matches = self.get_match_history(summoner_id, start_idx)

        for i, match in enumerate(matches):
            match_data = { 
                column : match["participants"][0]["stats"][column]
                for column in COLUMNS}
            match_data.update({
                "creation": match["gameCreation"],
                "duration": match["gameDuration"],
                "ARAM": match["gameMode"] == "ARAM"
            })
            matches[i] = match_data

        return MemberMatches(
            summoner_id=summoner_id,
            matches=matches)

    def run(self, start: int, nums: int = 0, save: bool = True):
        """入口函数
 
        Args:
            start: 数据爬取起始位置
            nums: 数据爬取数量
            save: 是否保存数据
        Returns:
            matches_data: 比赛数据
        """
        filename = f"{start}-{start + nums}_matches_data.json" if save else ""
        matches_data = self.get_matches_list(nums=nums, filename=filename)
        return self.get_matches_detail(matches_data, filename)


if __name__ == '__main__':
    spider = MatchGetter()
    spider.run(start=0, nums=1000)