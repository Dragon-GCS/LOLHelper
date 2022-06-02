from typing import List

MATCH_ITEM = [
    "assists", "deaths", "kills", "win"
]

def analysis_match_list(matches: List[dict]) -> float:
    """根据比赛记录获取召唤师的分数"""
    for match in matches:
        detail = match["participants"][0]["stats"]
    items = [""]
    return 1

def analysis_match_detail(match: dict) -> float:
    return 1


