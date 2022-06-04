from time import time
from typing import List, Tuple

TIME_LIMIT = 60 * 60 * 5    # 5 hours

def analysis_match_list(matches: List[dict], game_mode: str) -> Tuple[float, float, int]:
    """根据比赛记录计算召唤师kda、分均伤害和连胜/连败场次"""

    # total是总权重
    total,  stop = 0, False
    kills, deaths, assists, damages, repeats = 0, 0, 0, 0, 0
    for match in sorted(matches, key=lambda x: x["gameCreation"], reverse=True):
        if not match["gameMode"] == game_mode:
            continue
        weight = 1 if (time() / 1000 - match["gameCreation"]) < TIME_LIMIT else 0.2
        detail = match["participants"][0]["stats"]
        kills += detail["kills"] * weight
        deaths += detail["deaths"] * weight
        assists += detail["assists"] * weight
        damages += detail["totalDamageDealtToChampions"] * weight / match["gameDuration"] * 60
        total += weight
        prev = detail["win"] if locals().get("prev") is None else locals().get("prev")
        if not stop and detail["win"] == prev:
            repeats += 1 if prev else -1
        else:
            stop = True

    return (kills + assists) / (deaths or 1), damages / total, repeats
