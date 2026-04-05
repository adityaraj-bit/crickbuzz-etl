from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://www.cricbuzz.com"

# -----------------------
# SELENIUM PART
# -----------------------
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

all_matches = []

try:
    driver.get("https://www.cricbuzz.com/cricket-match/live-scores/recent-matches")

    # Click International tab
    international_tab = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'International')]"))
    )
    driver.execute_script("arguments[0].click();", international_tab)

    # Wait for matches
    wait.until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/live-cricket-scores/')]"))
    )

    # Get series blocks
    series_blocks = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'cbGrpHdrBkg')]/ancestor::div[1]"
    )

    for series in series_blocks:
        try:
            series_name = series.find_element(By.XPATH, ".//span").text

            match_links = series.find_elements(
                By.XPATH,
                ".//a[contains(@href,'/live-cricket-scores/')]"
            )

            for match in match_links:
                try:
                    link = match.get_attribute("href")
                    title = match.get_attribute("title")

                    if not title or title.strip() == "Live Score":
                        continue

                    teams = match.find_elements(
                        By.XPATH,
                        ".//span[contains(@class,'text-cbTxtPrim')]"
                    )
                    team_names = [t.text for t in teams if t.text and "-" not in t.text]

                    scores = match.find_elements(
                        By.XPATH,
                        ".//span[contains(@class,'font-medium')]"
                    )
                    score_values = [s.text for s in scores if s.text]

                    try:
                        status = match.find_element(
                            By.XPATH,
                            ".//span[contains(@class,'cbComplete')]"
                        ).text
                    except:
                        status = "N/A"

                    all_matches.append({
                        "series": series_name,
                        "match": title.strip(),
                        "teams": team_names,
                        "scores": score_values,
                        "status": status,
                        "link": link
                    })

                except:
                    continue

        except:
            continue

finally:
    driver.quit()


# -----------------------
# CLEAN DATA
# -----------------------
unique_matches = {m["link"]: m for m in all_matches}.values()
unique_matches = list(unique_matches)

live_links = [m["link"] for m in unique_matches]


# =============================
# BEAUTIFULSOUP PART
# =============================
all_data = []

for link in live_links:
    try:
        print(f"\n🔎 Scraping: {link}")

        res = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        # -----------------------
        # NAV LINKS
        # -----------------------
        nav_data = {}
        nav = soup.find("nav", {"id": "main-nav"})

        if nav:
            for a in nav.find_all("a"):
                name = a.text.strip()
                href = a.get("href")

                if href:
                    nav_data[name] = BASE_URL + href

        # -----------------------
        # PLAYER OF MATCH
        # -----------------------

        # -----------------------
# PLAYER OF MATCH (UPDATED LOGIC)
# -----------------------

        pom_name = None
        pom_link = None

        # ✅ NEW Cricbuzz layout (your working logic)
        sections = soup.find_all("div", class_="flex flex-col p-2 mx-2")

        for section in sections:
            label = section.find("div", class_="text-cbTxtSec text-xs")

            if label and "PLAYER OF THE MATCH" in label.text:
                player_tag = section.find("span")
                link_tag = section.find("a", href=True)

                if player_tag:
                    pom_name = player_tag.text.strip()

                if link_tag:
                    pom_link = BASE_URL + link_tag["href"]

                break


# ✅ FALLBACK (older Cricbuzz pages)
        if not pom_name:
            pom_section = soup.find("div", class_="cb-mom")
            if pom_section:
                a_tag = pom_section.find("a", href=True)
                if a_tag:
                    pom_name = a_tag.text.strip()
                    pom_link = BASE_URL + a_tag["href"]

        # -----------------------
        # STORE FINAL DATA
        # -----------------------
        all_data.append({
            "match_link": link,
            "nav_links": nav_data,
            "player_of_match": pom_name,
            "player_profile": pom_link
        })

        print("✅ Done")
        time.sleep(1)

    except Exception as e:
        print("❌ Error:", e)


# -----------------------
# FINAL OUTPUT
# -----------------------
print("\n🎯 TOTAL MATCHES SCRAPED:", len(all_data))

print(all_data)