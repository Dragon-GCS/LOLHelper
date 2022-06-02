from typing import List, Tuple

MATCH_ITEM = [
    "assists", "deaths", "kills", "win"
]

def analysis_match_list(matches: List[dict]) -> Tuple[float, float, int]:
    """根据比赛记录计算召唤师kda、分均伤害和连胜/连败场次"""

    kills, deaths, assists, damages = 0, 0, 0, 0
    matches = sorted(matches, key=lambda x: x["gameCreation"], reverse=True)
    repeats, prev, stop = 0, matches[0]["participants"][0]["stats"]["win"], False
    for match in sorted(matches, key=lambda x: x["gameCreation"], reverse=True):
        detail = match["participants"][0]["stats"]
        kills += detail["kills"]
        deaths += detail["deaths"]
        assists += detail["assists"]
        damages += detail["totalDamageDealtToChampions"] / match["gameDuration"] * 60
        if detail["win"] == prev and not stop:
            repeats += 1 if prev else -1
        else:
            stop = True

    return (kills + assists) / (deaths + 1), damages / len(matches), repeats
