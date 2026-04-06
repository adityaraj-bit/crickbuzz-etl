from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def get_matches():
    # IMPACT: surgical extraction to avoid garbage (sidebar news) and missing matches
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 15)

    all_matches = []
    
    try:
        driver.get("https://www.cricbuzz.com/cricket-match/live-scores/recent-matches")
        time.sleep(3)

        # 1. Select International Tab
        tab_xpath = "//div[contains(text(),'International')]"
        tabs = driver.find_elements(By.XPATH, tab_xpath)
        if not tabs:
            print("❌ International tab not found")
            return []
        
        driver.execute_script("arguments[0].click();", tabs[0])
        print("📡 Switched to International tab...")
        time.sleep(5) # Wait for page to refresh

        # 2. Extract Elements in Order
        # Combined XPath for series headers and primary match links
        xpath = "//div[contains(@class,'cbGrpHdrBkg')] | //a[contains(@class,'bg-cbWhite') and contains(@href,'/live-cricket-scores/') and contains(@title,' vs ')]"
        elements = driver.find_elements(By.XPATH, xpath)

        current_series = "Unknown Series"
        count = 0
        
        for el in elements:
            html = el.get_attribute("outerHTML")
            
            # --- CASE A: SERIES HEADER ---
            if "cbGrpHdrBkg" in html:
                current_series = el.text.strip()
                continue
            
            # --- CASE B: MATCH LINK ---
            link = el.get_attribute("href")
            title = el.get_attribute("title")
            
            # Strict validation: Must contain ' vs ' in title to be a primary match link
            if " vs " not in title:
                continue

            # Extraction of Teams (Surgical Depth-Specific XPath to avoid scores)
            # Match names are at div > div > div > span, while scores are at div > div > span
            teams = el.find_elements(By.XPATH, ".//div/div/div/span")
            team_names = [t.text.strip() for t in teams if t.text and not any(char.isdigit() for char in t.text)]
            
            # Extraction of Status (Result Text)
            try:
                status = el.find_element(By.XPATH, ".//span[contains(@class,'cbComplete')]").text
            except:
                status = "N/A"

            match_data = {
                "series": current_series,
                "match": title.strip(),
                "status": status,
                "link": link
            }

            if len(team_names) >= 2:
                match_data["team1"] = team_names[0]
                match_data["team2"] = team_names[1]

            all_matches.append(match_data)
            count += 1

        print(f"✅ Found {count} match entries in DOM")

    finally:
        driver.quit()

    # Final deduplication and sanity check
    unique_matches = {m["link"]: m for m in all_matches}.values()
    final_list = list(unique_matches)
    print(f"🎯 Total unique matches after filtering: {len(final_list)}")
    return final_list
