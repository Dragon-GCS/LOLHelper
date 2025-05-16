import json
import sys
from enum import StrEnum
from pathlib import Path

VERSION = "v1.1"
if hasattr(sys, "frozen"):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).parent.parent.resolve()

AUTO_CONFIRM = True
AUTO_ANALYSIS = True
AUTO_PICKS = []
AUTO_PICK_SWITCH = True
AUTO_PICK_CACHE = ROOT / "champions.json"

SAVE_MATCH = False
MATCH_FILE = ROOT / "matches.txt"
# fmt: off
SAVE_ITEM = {
    "assists", "champLevel", "damageSelfMitigated", "deaths", "firstBloodKill",
    "goldEarned", "killingSprees", "kills", "largestMultiKill",
    "longestTimeSpentLiving", "pentaKills", "quadraKills", "totalDamageDealt",
    "totalDamageDealtToChampions", "totalDamageTaken", "totalHeal", "totalMinionsKilled",
    "tripleKills", "trueDamageDealt", "win",
}
# fmt: on

if AUTO_PICK_CACHE.exists():
    with AUTO_PICK_CACHE.open("r", encoding="utf8") as f:
        AUTO_PICKS = list(json.load(f)["selected"].keys())

PROCESS_NAME = "LeagueClientUx.exe"


class GameMode(StrEnum):
    ARAM = "ARAM"
    CLASSIC = "CLASSIC"


class Route(StrEnum):
    # https://www.mingweisamuel.com/lcu-schema/
    GameFlow = "/lol-gameflow/v1/gameflow-phase"
    ChampionBench = "/lol-lobby-team-builder/champ-select/v1/session"
    BpSession = "/lol-champ-select/v1/session"
    # 选人信息
    AddFriend = "/lol-chat/v1/friend-requests"  # POST
    AcceptGame = "/lol-matchmaking/v1/ready-check/accept"  # post
    BlueEssence = "/lol-inventory/v1/wallet/lol_blue_essence"
    BpChampion = "/lol-champ-select/v1/session/actions/{actionId}"  # patch
    SwapChampion = "/lol-champ-select/v1/session/bench/swap/{championId}"
    CancelAddFriend = "/lol-chat/v1/friend-requests/{summonerId}"  # Delete
    # 英雄信息
    Champions = "/lol-game-data/assets/v1/champions/{id}.json"
    AllChampions = "/lol-champions/v1/owned-champions-minimal"
    CurrentChampion = "/lol-champ-select/v1/current-champion"
    # 房间信息
    Session = "/lol-gameflow/v1/session"
    ChatInfo = "/lol-chat/v1/conversations/{roomId}/messages"
    # 当前所有好友对话 id: conversation-id以及最后回复内容
    Conversations = "/lol-chat/v1/conversations"
    # 指定聊天的所有内容    post: {"body": "message", "type": "chat"}
    ConversationMsg = "/lol-chat/v1/conversations/{conversationId}/messages"
    CurrentEnvironment = "/riotclient/v1/crash-reporting/environment"
    CurrentSummoner = "/lol-summoner/v1/current-summoner"
    MatchDetail = "/lol-match-history/v1/games/{gameId}"
    MatchList = (
        "/lol-match-history/v1/products/lol/{puuid}/matches?begIndex={begIdx}&endIndex={endIdx}"
    )
    Summoner = "/lol-summoner/v1/summoners-by-puuid-cached/{puuid}"
    SummonerByName = "/lol-summoner/v1/summoners?name={name}"
    ProfileIcon = "/lol-game-data/assets/v1/profile-icons/{id}.jpg"
    RankedStats = "/lol-ranked/v1/ranked-stats/{puuid}"
    Summoners = "/lol-summoner/v2/summoners?ids={ids}"
