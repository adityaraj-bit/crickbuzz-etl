import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_soup(url):
    res = requests.get(url, headers=HEADERS)
    return BeautifulSoup(res.text, "html.parser")


# -------------------------------
# PARSE BATTING
# -------------------------------
def parse_batting(innings):
    batting_data = []

    rows = innings.select("div.scorecard-bat-grid")

    for row in rows[1:]:  # skip header
        name_tag = row.find("a")
        if not name_tag:
            continue

        name = name_tag.text.strip()

        dismissal_tag = row.select_one("div.text-cbTxtSec")
        dismissal = dismissal_tag.text.strip() if dismissal_tag else "not out"

        # Extract bowler name from dismissal string
        # Examples: "b Benny Howell", "c Umar Akmal b Benny Howell", "c & b Benny Howell"
        bowler_name = None
        if " b " in dismissal or dismissal.startswith("b "):
            import re
            # Find the last 'b ' or 'b ' at the start
            match = re.search(r'\bb\s+([^,()]+)$', dismissal)
            if match:
                bowler_name = match.group(1).strip()

        # get all stat cells (numbers)
        cols = row.find_all("div")
        values = [c.text.strip() for c in cols if c.text.strip()]

        # Filter numeric values
        stats = []
        for v in values:
            if v.replace('.', '', 1).isdigit():
                stats.append(v)

        if len(stats) < 5:
            continue

        batting_data.append({
            "name": name,
            "dismissal": dismissal,
            "bowler": bowler_name,
            "runs": stats[0],
            "balls": stats[1],
            "4s": stats[2],
            "sixes": stats[3], # Schema is sixes
            "sr": stats[4]
        })

    return batting_data


# -------------------------------
# PARSE BOWLING
# -------------------------------
def parse_bowling(innings):
    bowling_data = []

    rows = innings.select("div.scorecard-bowl-grid")

    for row in rows[1:]:
        name_tag = row.find("a")
        if not name_tag:
            continue

        name = name_tag.text.strip()

        # Only visible stat cells
        cols = row.select("div.flex.justify-center.items-center")

        values = [c.text.strip() for c in cols]

        # Handle 5-column vs 7-column cases
        if len(values) == 5:
            # NB & WD missing
            overs, maidens, runs, wickets, economy = values
            no_balls = "0"
            wides = "0"

        elif len(values) >= 7:
            overs, maidens, runs, wickets, no_balls, wides, economy = values[:7]

        else:
            continue

        bowling_data.append({
            "name": name,
            "overs": overs,
            "maidens": maidens,
            "runs": runs,
            "wickets": wickets,
            "no_balls": no_balls,
            "wides": wides,
            "economy": economy
        })

    return bowling_data

# -------------------------------
# MAIN PARSER
# -------------------------------
def parse_scorecard(url):
    try:
        soup = get_soup(url)

        match_data = []

        # Find all innings dynamically
        innings_list = []
        seen = set()

        for i in soup.select("div[id^=scard-team-]"):
            key = i.get("id")
            if key not in seen:
                seen.add(key)
                innings_list.append(i)

        if not innings_list:
            print("⚠️ No innings found:", url)
            return None

        for innings in innings_list:
            # Get team name and total score string
            # Header looks like: Galle Marvels 53-4 (5.5 Ov)
            header = innings.find_previous("div", id=lambda x: x and x.startswith("team-"))

            team_name = None
            total_score = {"runs": 0, "wickets": 10, "overs": 0.0}

            if header:
                # Team Name
                team_tag = header.find("div", class_="tb:block")
                if team_tag:
                    team_name = team_tag.text.strip()
                else:
                    # Fallback to any font-bold div
                    team_tag = header.find("div", class_="font-bold")
                    if team_tag: team_name = team_tag.text.strip()
                
                # Score: 53-4
                score_tag = header.find("span", class_="font-bold")
                if score_tag:
                    score_text = score_tag.text.strip()
                    # Match "Runs-Wickets" or "Runs/Wickets" or just "Runs"
                    import re
                    rw_match = re.search(r'(\d+)(?:[-/](\d+))?', score_text)
                    if rw_match:
                        total_score["runs"] = rw_match.group(1)
                        total_score["wickets"] = rw_match.group(2) or "10"
                
                # Overs: (5.5 Ov)
                over_tags = header.find_all("span")
                for ot in over_tags:
                    if "Ov" in ot.text:
                        import re
                        over_match = re.search(r'(\d+\.?\d*)', ot.text)
                        if over_match:
                            total_score["overs"] = over_match.group(1)
                            break

            data = {
                "team": team_name,
                "total": total_score,
                "batting": parse_batting(innings),
                "bowling": parse_bowling(innings)
            }

            match_data.append(data)

        return match_data
    except Exception as e:
        print("❌ scorecard error:", e)
        return None