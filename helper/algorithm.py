from typing import List

MATCH_ITEM = [
    "assists", "deaths", "kills", "win"
]

def calculate_wining_bonus(matches: List[dict]) -> float:
    for match in matches:
        detail = match["participants"][0]["stats"]
    items = [""]
    return 1


