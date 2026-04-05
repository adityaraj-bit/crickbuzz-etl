import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cricbuzz.com"


def get_match_details(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        nav_links = {}

        nav = soup.find("nav", {"id": "main-nav"})
        if nav:
            for a in nav.find_all("a"):
                name = a.text.strip()
                href = a.get("href")

                if href:
                    nav_links[name] = BASE_URL + href

        # -----------------------
        # PLAYER OF MATCH
        # -----------------------
        player_of_match = None
        sections = soup.find_all("div", class_="flex flex-col p-2 mx-2")

        for section in sections:
            label = section.find("div", class_="text-cbTxtSec text-xs")
            if label and "PLAYER OF THE MATCH" in label.text:
                player_tag = section.find("span")
                if player_tag:
                    player_of_match = player_tag.text.strip()
                    break

        return {
            "match_link": url,
            "nav_links": nav_links,
            "scorecard_url": nav_links.get("Scorecard") or nav_links.get("Score Card"),
            "info_url": nav_links.get("Info"),
            "player_of_match": player_of_match
        }

    except Exception as e:
        print("❌ match_details error:", e)
        return None