import requests
from bs4 import BeautifulSoup

url = "https://www.cricbuzz.com/live-cricket-scores/148254/tan-vs-shn-10th-match-icc-mens-t20-world-cup-africa-sub-regional-qualifier-b-2026"

headers = {
    "User-Agent": "Mozilla/5.0"
}

# Fetch page
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# -----------------------------
# FIND PLAYER OF THE MATCH
# -----------------------------
player_name = None

# Find all sections and locate the correct one
sections = soup.find_all("div", class_="flex flex-col p-2 mx-2")

for section in sections:
    label = section.find("div", class_="text-cbTxtSec text-xs")
    
    if label and "PLAYER OF THE MATCH" in label.text:
        player_tag = section.find("span")
        if player_tag:
            player_name = player_tag.text.strip()
            break

# -----------------------------
# OUTPUT
# -----------------------------
if player_name:
    print("Player of the Match:", player_name)
else:
    print("Player of the Match not found")