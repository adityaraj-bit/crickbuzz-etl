import requests
from bs4 import BeautifulSoup
import re

def scrape_player_profile(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        data = {}

        # =========================
        # HEADER BLOCK
        # =========================
        header = soup.find("div", class_=lambda x: x and "items-center" in x and "gap-4" in x)

        if not header:
            print(f"❌ Header not found for {url}")
            return None

        # =========================
        # NAME
        # =========================
        name = None
        flex_col = header.find("div", class_=lambda x: x and "flex-col" in x)

        if flex_col:
            name_tag = flex_col.find("span")
            if name_tag:
                name = name_tag.get_text(strip=True)

        data["name"] = name

        # =========================
        # COUNTRY
        # =========================
        country = "Unknown"

        if flex_col:
            country_div = flex_col.find("div", class_=lambda x: x and "inline-flex" in x)
            if country_div:
                country_span = country_div.find_all("span")
                if country_span:
                    country = country_span[-1].get_text(strip=True)

        data["country"] = country

        # =========================
        # PERSONAL INFO (Robust Label -> Value Search)
        # =========================
        personal_info = {}
        
        # Labels we care about and their canonical keys
        label_map = {
            "Born": "Born",
            "Birth Place": "Birth Place",
            "Role": "Role",
            "Playing Role": "Role",
            "Batting Style": "Batting Style",
            "Bowling Style": "Bowling Style",
            "Height": "Height"
        }

        # Find all divs that might contain labels/values (common Cricbuzz pattern)
        info_divs = soup.find_all("div", class_=lambda x: x and ("cb-col-40" in x or "cb-col-60" in x or "cb-col-100" in x))
        
        for i, div in enumerate(info_divs):
            text = div.get_text(strip=True).strip(":")
            if text in label_map:
                canonical_key = label_map[text]
                # The value is usually in the next div (cb-col-60)
                if i + 1 < len(info_divs):
                    val = info_divs[i+1].get_text(strip=True)
                    personal_info[canonical_key] = val

        # Fallback: If the above failed, try searching for text directly
        if not personal_info:
            for label, canonical_key in label_map.items():
                label_tag = soup.find(text=re.compile(f"^{label}$", re.I))
                if label_tag:
                    parent = label_tag.find_parent("div")
                    if parent:
                        # Value is often in the sibling div
                        next_div = parent.find_next_sibling("div")
                        if next_div:
                            personal_info[canonical_key] = next_div.get_text(strip=True)

        data["personal_info"] = personal_info

        return data
    except Exception as e:
        print(f"❌ Error scraping profile {url}: {e}")
        return None
