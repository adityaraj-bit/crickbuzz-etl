import requests
from bs4 import BeautifulSoup
import re


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_soup(url):
    res = requests.get(url, headers=HEADERS)
    return BeautifulSoup(res.text, "html.parser")


# -------------------------------
# HELPERS
# -------------------------------
def extract_role(name_text):
    """Extract (c) and (wk) from name and returns (clean_name, roles)"""
    roles = []
    lower_name = name_text.lower()
    if "(c)" in lower_name: roles.append("captain")
    if "(wk)" in lower_name: roles.append("wicketkeeper")
    
    # Also handle (c & wk)
    if "(c & wk)" in lower_name:
        if "captain" not in roles: roles.append("captain")
        if "wicketkeeper" not in roles: roles.append("wicketkeeper")

    clean_name = re.sub(r"\(c\s*&\s*wk\)", "", name_text, flags=re.I)
    clean_name = re.sub(r"\(c\)", "", clean_name, flags=re.I)
    clean_name = re.sub(r"\(wk\)", "", clean_name, flags=re.I)
    
    # Simple regex for just the markers if the above fails
    clean_name = clean_name.replace(",", "").strip()
    return clean_name, roles


# -------------------------------
# PARSE BATTING
# -------------------------------
def parse_batting(innings):
    batting_data = []

    rows = innings.select("div.scorecard-bat-grid")
    
    # If standard grid not found, skip header logic
    if not rows:
        return batting_data

    for row in rows[1:]:  # Skip header row
        name_tag = row.find("a")
        if not name_tag:
            continue

        raw_name = name_tag.text.strip()
        name, roles = extract_role(raw_name)
        profile = name_tag.get("href")
        if profile:
            profile = "https://www.cricbuzz.com" + profile

        dismissal_tag = row.select_one("div.text-cbTxtSec")
        dismissal = dismissal_tag.text.strip() if dismissal_tag else "not out"

        # Resolve bowler from dismissal string
        bowler_name = None
        if " b " in dismissal or dismissal.startswith("b "):
            match = re.search(r'\bb\s+([^,()]+)$', dismissal)
            if match:
                bowler_name = match.group(1).strip()

        # Get all stat cells
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
            "roles": roles,
            "profile": profile,
            "dismissal": dismissal,
            "bowler": bowler_name,
            "runs": stats[0],
            "balls": stats[1],
            "4s": stats[2],
            "sixes": stats[3],
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

        raw_name = name_tag.text.strip()
        name, roles = extract_role(raw_name)
        profile = name_tag.get("href")
        if profile:
            profile = "https://www.cricbuzz.com" + profile

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
            "roles": roles,
            "profile": profile,
            "overs": overs,
            "maidens": maidens,
            "runs": runs,
            "wickets": wickets,
            "no_balls": no_balls,
            "wides": wides,
            "economy": economy
        })

    return bowling_data


def parse_did_not_bat(innings):
    dnb_list = []

    label = innings.find(string=lambda x: x and "Did not Bat" in x)

    if not label:
        return dnb_list

    parent = label.find_parent("div")
    players_container = parent.find_next_sibling("div") if parent else None

    if not players_container:
        return dnb_list

    for a in players_container.find_all("a"):
        raw_name = a.text.replace(",", "").strip()
        if not raw_name:
            continue
            
        name, roles = extract_role(raw_name)
        profile = a.get("href")
        if profile:
            profile = "https://www.cricbuzz.com" + profile

        dnb_list.append({
            "name": name,
            "roles": roles,
            "profile": profile
        })

    return dnb_list


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
            # Get team name and score from header
            header = innings.find_previous("div", id=lambda x: x and x.startswith("team-"))

            team_name = None
            total_score = {"runs": 0, "wickets": 10, "overs": 0.0}

            if header:
                team_tag = header.find("div", class_="tb:block") or header.find("div", class_="font-bold")
                if team_tag: team_name = team_tag.text.strip()
                
                score_tag = header.find("span", class_="font-bold")
                if score_tag:
                    score_text = score_tag.text.strip()
                    rw_match = re.search(r'(\d+)(?:[-/](\d+))?', score_text)
                    if rw_match:
                        total_score["runs"] = rw_match.group(1)
                        total_score["wickets"] = rw_match.group(2) or "10"
                
                over_tags = header.find_all("span")
                for ot in over_tags:
                    if "Ov" in ot.text:
                        over_match = re.search(r'(\d+\.?\d*)', ot.text)
                        if over_match:
                            total_score["overs"] = over_match.group(1)
                            break

            data = {
                "team": team_name,
                "total": total_score,
                "batting": parse_batting(innings),
                "bowling": parse_bowling(innings),
                "dnb": parse_did_not_bat(innings)
            }

            match_data.append(data)

        return match_data
    except Exception as e:
        print("❌ scorecard error:", e)
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    url = "https://www.cricbuzz.com/live-cricket-scorecard/151481/"
    data = parse_scorecard(url)
    import json
    print(json.dumps(data, indent=2))
