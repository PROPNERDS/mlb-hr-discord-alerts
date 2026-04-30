import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
today = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")
STATE_FILE = f"seen_hrs_{today}.json"

def get_today_games():
    today = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    data = requests.get(url, timeout=20).json()

    games = []
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            status = game.get("status", {}).get("abstractGameState", "")
            if status in ["Live", "Final"]:
                games.append(game["gamePk"])
    return games

def load_seen():
    try:
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(list(seen)), f, indent=2)

def send_discord(message):
    response = requests.post(WEBHOOK_URL, json={"content": message}, timeout=20)
    response.raise_for_status()

def get_statcast_data(play):
    distance = "N/A"
    ev = "N/A"
    la = "N/A"

    for event in play.get("playEvents", []):
        hit_data = event.get("hitData", {})
        if hit_data:
            distance = hit_data.get("totalDistance", "N/A")
            ev = hit_data.get("launchSpeed", "N/A")
            la = hit_data.get("launchAngle", "N/A")

    return distance, ev, la

def check_game(game_pk, seen):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    data = requests.get(url, timeout=20).json()

    game_data = data.get("gameData", {})
    live_data = data.get("liveData", {})

    venue = game_data.get("venue", {}).get("name", "Unknown Park")

    teams = game_data.get("teams", {})
    away_team = teams.get("away", {}).get("teamName", "Away")
    home_team = teams.get("home", {}).get("teamName", "Home")

    linescore = live_data.get("linescore", {})
    away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)
    home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)

    plays = live_data.get("plays", {}).get("allPlays", [])

    for play in plays:
        result = play.get("result", {})
        event_type = result.get("eventType", "")
        event_name = result.get("event", "")

        if event_type != "home_run" and event_name != "Home Run":
            continue

        play_id = f"{game_pk}-{play.get('atBatIndex')}"
        if play_id in seen:
            continue

        batter = play.get("matchup", {}).get("batter", {}).get("fullName", "Unknown Batter")
        pitcher = play.get("matchup", {}).get("pitcher", {}).get("fullName", "Unknown Pitcher")

        about = play.get("about", {})
        inning = about.get("inning", "?")
        half = about.get("halfInning", "").title()

        if half == "Top":
            batting_team = away_team
        elif half == "Bottom":
            batting_team = home_team
        else:
            batting_team = "Unknown Team"

        description = result.get("description", "Home run!")

        rbi = result.get("rbi", 1)
        if rbi == 4:
            hr_type = "GRAND SLAM 🚨🚨🚨"
        elif rbi == 3:
            hr_type = "3-RUN BLAST"
        elif rbi == 2:
            hr_type = "2-RUN SHOT"
        else:
            hr_type = "SOLO SHOT"

        distance, ev, la = get_statcast_data(play)

        message = (
            "🚨⚾ **HOME RUN ALERT** ⚾🚨\n\n"
            f"💣 **{batter}** — {batting_team}\n"
            f"🔥 **{hr_type}**\n\n"
            f"📏 **Distance:** {distance} FT\n"
            f"🚀 **Exit Velo:** {ev} MPH\n"
            f"📐 **Launch Angle:** {la}°\n"
            f"👤 **Pitcher:** {pitcher}\n\n"
            f"🕒 **Inning:** {half} {inning}\n"
            f"📍 **Ballpark:** {venue}\n"
            f"📊 **Score:** {away_team} {away_score} - {home_team} {home_score}\n\n"
            f"📝 {description}\n\n"
            "🍻 **Prop Nerds Bomb Detector is live.**\n"
            "#PropNerds"
        )

        send_discord(message)
        seen.add(play_id)

def main():
    seen = load_seen()
    games = get_today_games()
    send_discord(f"✅ HR Bot checked {len(games)} MLB games.")

    send_discord(f"✅ HR Bot checked {len(games)} MLB games today.")

    if not games:
        send_discord("⚠️ HR Bot check ran, but no live/final MLB games were found today.")
        return

    for game_pk in games:
        check_game(game_pk, seen)

    save_seen(seen)

if __name__ == "__main__":
    main()
