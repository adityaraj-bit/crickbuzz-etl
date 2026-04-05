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
            "runs": stats[0],
            "balls": stats[1],
            "4s": stats[2],
            "6s": stats[3],
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

    for innings in innings_list:
        # Get team name
        header = innings.find_previous("div", id=lambda x: x and x.startswith("team-"))

        team_name = None
        if header:
            team_tag = header.find_all("div")[1]
            team_name = team_tag.text.strip()

        data = {
            "team": team_name,
            "batting": parse_batting(innings),
            "bowling": parse_bowling(innings)
        }

        match_data.append(data)

    return match_data


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    url = "https://www.cricbuzz.com/live-cricket-scorecard/148254/"

    data = parse_scorecard(url)

    import json
    print(json.dumps(data, indent=2))