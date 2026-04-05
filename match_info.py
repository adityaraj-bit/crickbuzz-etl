import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cricbuzz.com"


def parse_match_info(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        data = {
            "info": {},
            "squads": {},
            "venue": {}
        }

        # =========================
        # INFO SECTION (SAFE)
        # =========================
        info_section = soup.find("div", class_="wb:px-4")

        if not info_section:
            # fallback to whole page
            info_section = soup

        rows = info_section.find_all("div", class_="facts-row-grid")

        for row in rows:
            cols = row.find_all("div")
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                data["info"][key] = value

        # =========================
        # SQUADS (WITH PROFILE LINKS)
        # =========================
        squads = {}

        # ✅ Scope to info_section as in your script
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

                    # detect roles (Matched to your testing script)
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
                if players:
                    squads[team_name] = {
                        "playing_xi": players[:11],
                        "bench": players[11:]
                    }

        data["squads"] = squads

        # =========================
        # VENUE GUIDE
        # =========================
        venue_span = soup.find("span", string="VENUE GUIDE")

        if venue_span:
            try:
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
                            data["venue"][key] = value
            except:
                pass

        # =========================
        # FINAL VALIDATION
        # =========================
        if not data["info"] and not data["squads"]:
            print("⚠️ Empty info page:", url)
            return None

        return data

    except Exception as e:
        print("❌ parse_match_info error:", e)
        return None