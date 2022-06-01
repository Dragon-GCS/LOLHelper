from sys import stdout
import time
import json
from helper.lcu import LcuClient

from loguru import logger
logger.remove()
logger.add(stdout, level="INFO")

def main():
    client = LcuClient()
    with open("all_matches.json", "r", encoding="utf8") as f:
        matches = json.load(f)
    with open("champions.json", "r", encoding="utf8") as f:
        champions = json.load(f)

    details = []
    for i, match in enumerate(matches):
        if match["gameMode"] != "ARAM":
            continue
        detail = client.get_match_detail(match["gameId"])
        if not detail.get("participantIdentities"):
            time.sleep(1)
            detail = client.get_match_detail(match["gameId"])
        participantId = {
            player["participantId"]: {
                "summonerId": player["player"]["summonerId"],
                "summonerName": player["player"]["summonerName"],
            }
            for player in detail["participantIdentities"]}
        participants = {
            participant["participantId"]: {
                "championId": participant["championId"],
                "teamId": participant["teamId"],
            }
            for participant in detail["participants"]
        }
        for key in participantId.keys():
            participantId[key]["teamId"] = participants[key]["teamId"]
            champion_id = participants[key]["championId"]
            participantId[key]["championId"] = champion_id
            try:
                participantId[key]["championName"] = champions[str(champion_id)]
            except KeyError:
                champion_name = client.get_champion_name_by_id(champion_id)
                participantId[key]["championName"] = champion_name
                champions[str(participants[key])] = champion_name

        details.append(participantId)
        time.sleep(0.2)
        print(f"{i}/{len(matches)}", end="\r")
    with open("champions.json", "w", encoding="utf8") as f:
        json.dump(champions, f, ensure_ascii=False)

    with open("all_match_history.json", "w", encoding="utf8") as f:
        json.dump(details, f, ensure_ascii=False)


if __name__ == '__main__':
    main()
    # client = LcuClient()
    # match = client.get_match_detail("2393915136")
    # print(match)
    # print(match["participantIdentities"])