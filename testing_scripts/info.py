import requests
from bs4 import BeautifulSoup
import json

url = "https://www.cricbuzz.com/cricket-match-facts/122847/nzw-vs-rsaw-2nd-odi-south-africa-women-tour-of-new-zealand-2026"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

data = {}

# =========================
# INFO SECTION
# =========================
info_section = soup.find("div", class_="wb:px-4")

info_data = {}
rows = info_section.find_all("div", class_="facts-row-grid")

for row in rows:
    cols = row.find_all("div")
    if len(cols) >= 2:
        key = cols[0].get_text(strip=True)
        value = cols[1].get_text(strip=True)
        info_data[key] = value

data["info"] = info_data



# =========================
# SQUADS (WITH PROFILE LINKS)
# =========================
BASE_URL = "https://www.cricbuzz.com"
squads = {}

squad_blocks = info_section.find_all("div", class_="hidden")

for block in squad_blocks:
    team_sections = block.find_all("div", class_="grid")

    for team in team_sections:
        title_div = team.find("div", class_="font-bold")
        if not title_div:
            continue

        team_name = title_div.get_text(strip=True).replace("squad", "").strip()

        players = []

        # ✅ ONLY players (skip support staff)
        player_section = team.find("div", string="Players")
        if not player_section:
            continue

        player_links = player_section.find_next("div").find_all("a")

        for a in player_links:
            name = a.get_text(strip=True).replace(",", "")
            href = a.get("href")

            # Full profile URL
            profile_link = BASE_URL + href if href else None

            # detect roles
            if "(c)" in name:
                role = "Captain"
            elif "(wk)" in name:
                role = "Wicketkeeper"
            else:
                role = "Player"

            clean_name = name.replace("(c)", "").replace("(wk)", "").strip()

            players.append({
                "name": clean_name,
                "role": role,
                "profile": profile_link
            })

        # Split Playing XI & Bench
        playing_xi = players[:11]
        bench = players[11:]

        squads[team_name] = {
            "playing_xi": playing_xi,
            "bench": bench
        }

data["squads"] = squads


# =========================
# VENUE GUIDE
# =========================
venue_data = {}

venue_span = soup.find("span", string="VENUE GUIDE")

if venue_span:
    header_div = venue_span.find_parent("div")
    container_div = header_div.find_parent("div")

    venue_parent = container_div.find_next_sibling("div")

    if venue_parent:
        rows = venue_parent.find_all("div", class_="facts-row-grid")

        for row in rows:
            cols = row.find_all("div")
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                venue_data[key] = value

data["venue"] = venue_data


# =========================
# OUTPUT
# =========================
print(json.dumps(data, indent=2))