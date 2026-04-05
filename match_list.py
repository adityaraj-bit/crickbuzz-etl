from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def get_matches():
    # EXACTLY AS IN main_old.py
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
                            "status": status,
                            "link": link
                        })

                    except:
                        continue

            except:
                continue

    finally:
        driver.quit()

    # remove duplicates
    unique_matches = {m["link"]: m for m in all_matches}.values()
    return list(unique_matches)