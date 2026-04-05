from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

try:
    # -----------------------
    # OPEN PAGE
    # -----------------------
    driver.get("https://www.cricbuzz.com/cricket-match/live-scores/recent-matches")
    time.sleep(5)

    # -----------------------
    # CLICK INTERNATIONAL
    # -----------------------
    international_tab = driver.find_element(
        By.XPATH,
        "//div[contains(text(),'International')]"
    )
    driver.execute_script("arguments[0].click();", international_tab)
    time.sleep(5)

    print("\n🎯 INTERNATIONAL MATCHES:\n")

    # -----------------------
    # GET ALL SERIES BLOCKS
    # -----------------------
    series_blocks = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'cbGrpHdrBkg')]/ancestor::div[1]"
    )

    for series in series_blocks:
        try:
            # -----------------------
            # SERIES NAME
            # -----------------------
            series_name = series.find_element(By.XPATH, ".//span").text
            print(f"\n🏆 Series: {series_name}")

            # -----------------------
            # MATCH LINKS INSIDE SERIES
            # -----------------------
            match_links = series.find_elements(
                By.XPATH,
                ".//a[contains(@href,'/live-cricket-scores/')]"
            )

            for match in match_links:
                try:
                    link = match.get_attribute("href")

                    # Match title
                    title = match.get_attribute("title")

                    # Teams
                    teams = match.find_elements(By.XPATH, ".//span[contains(@class,'text-cbTxtPrim')]")
                    team_names = [t.text for t in teams if t.text]

                    # Scores
                    scores = match.find_elements(By.XPATH, ".//span[contains(@class,'font-medium')]")
                    score_values = [s.text for s in scores if s.text]

                    # Status
                    try:
                        status = match.find_element(
                            By.XPATH,
                            ".//span[contains(@class,'cbComplete')]"
                        ).text
                    except:
                        status = "N/A"

                    print({
                        "match": title,
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