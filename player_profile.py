import requests
from bs4 import BeautifulSoup


def scrape_player_profile(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        data = {
            "name": None,
            "country": None,
            "personal_info": {}
        }

        # =========================
        # HEADER BLOCK
        # =========================
        header = soup.find("div", class_=lambda x: x and "items-center" in x and "gap-4" in x)

        if not header:
            print("❌ Header not found")
            return None

        # =========================
        # NAME
        # =========================
        flex_col = header.find("div", class_=lambda x: x and "flex-col" in x)

        if flex_col:
            name_tag = flex_col.find("span")
            if name_tag:
                data["name"] = name_tag.get_text(strip=True)

        # =========================
        # COUNTRY
        # =========================
        if flex_col:
            country_div = flex_col.find("div", class_=lambda x: x and "inline-flex" in x)
            if country_div:
                country_span = country_div.find_all("span")
                if country_span:
                    data["country"] = country_span[-1].get_text(strip=True)

        # =========================
        # PERSONAL INFO
        # =========================
        personal_info = {}

        # Find the section containing PERSONAL INFORMATION
        section = None

        for tag in soup.find_all(string=lambda text: "PERSONAL INFORMATION" in text):
            section = tag.find_parent("div")
            break

        if section:
            # Go one level up to include full block
            parent = section.find_parent("div")

            # Find rows inside this section only
            rows = parent.find_all("div", class_=lambda x: x and "flex" in x)

            for row in rows:
                cols = row.find_all("div", recursive=False)

                if len(cols) == 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)

                    # ✅ Clean filters
                    if (
                        key and val
                        and len(key) < 25
                        and key.lower() not in ["batting", "bowling"]
                    ):
                        personal_info[key] = val

        data["personal_info"] = personal_info
        return data

    except Exception as e:
        print(f"❌ player profile error: {e}")
        return None