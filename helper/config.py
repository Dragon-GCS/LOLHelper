from enum import Enum

DEBUG = False
AUTO_CONFIRM = True
AUTO_PICKS = []


PROCESS_NAME = "LeagueClientUx.exe"
class GameMode:
    ARAM = "ARAM"
    CLASSIC = "CLASSIC"


ROUTE = {
    "GameFlow": "/lol-gameflow/v1/gameflow-phase",
    "ChampionBench": "/lol-lobby-team-builder/champ-select/v1/session",
    # 选人信息
    "BpSession": "/lol-champ-select/v1/session",
    "add-friend": "/lol-chat/v1/friend-requests",  # POST
    "accept-game": "/lol-matchmaking/v1/ready-check/accept",    # post
    "blue-essence": "/lol-inventory/v1/wallet/lol_blue_essence",
    "bp-champion": "/lol-champ-select/v1/session/actions/{actionId}",  # patch
    "swap-champion": "/lol-champ-select/v1/session/bench/swap/{championId}",
    "cancel-add-friend": "/lol-chat/v1/friend-requests/{summonerId}",  # Delete
    # 英雄信息
    "champions": "/lol-game-data/assets/v1/champions/{id}.json",
    "current-champion": "/lol-champ-select/v1/current-champion",
    # 房间信息
    "session": "/lol-gameflow/v1/session",
    "chat-info": "/lol-chat/v1/conversations/{roomId}/messages",
    # 当前所有好友对话 id: conversation-id以及最后回复内容
    "conversations": "/lol-chat/v1/conversations",
    # 指定聊天的所有内容    post: {"body": "message", "type": "chat"}
    "conversation-msg": "/lol-chat/v1/conversations/{conversationId}/messages",
    "current-environment": "/riotclient/v1/crash-reporting/environment",
    "current-summoner": "/lol-summoner/v1/current-summoner",
    "game-flow": "/lol-gameflow/v1/gameflow-phase",
    "match-detail": "/lol-match-history/v1/games/{gameId}",
    "match-list": "/lol-match-history/v3/matchlist/account/{summonerId}?begIndex={begIdx}&endIndex={endIdx}",
    "summoner": "/lol-summoner/v1/summoners/{summonerId}",
    "summoner-by-name": "/lol-summoner/v1/summoners?name={name}",
    "profile-icon": "/lol-game-data/assets/v1/profile-icons/{id}.jpg",
    "ranked-stats": "/lol-ranked/v1/ranked-stats/{summonerId}",
    # ids = ','.join(summonerIds)
    "summoners": "/lol-summoner/v2/summoners?ids={ids}",
}
