import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL = "https://www.cricbuzz.com"

class SquadScraper:
    def __init__(self, headless=True):
        self.options = Options()
        if headless:
            self.options.add_argument("--headless")
        # Ensure common production flags
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")
        self.driver = None

    def __enter__(self):
        self.driver = webdriver.Chrome()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()

    def get_selenium_soup(self, url):
        if not url: return None
        try:
            self.driver.get(url)
            # Wait for either profile links or the facts grid
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/profiles/'], .facts-row-grid"))
                )
            except TimeoutException:
                print(f"⚠️ Timeout waiting for facts grid on {url}")
                pass 
            
            time.sleep(1) # Small buffer for dynamic elements
            return BeautifulSoup(self.driver.page_source, "html.parser")
        except Exception as e:
            print(f"⚠️ Selenium error fetching {url}: {e}")
            return None

    def parse_player(self, name_text):
        name = name_text.strip()
        role = "player"
        if "(c)" in name.lower(): role = "captain"
        elif "(wk)" in name.lower(): role = "wicketkeeper"
        
        # Clean name of markers
        clean_name = re.sub(r"\((c|wk)\)", "", name, flags=re.IGNORECASE).strip()
        return clean_name, role

    def extract_squads_from_soup(self, soup):
        squads = {}
        if not soup: return squads

        # 1. Identify Team Names from headers
        team_headers = soup.select(".cb-mtch-squads-team-name")
        team_names = [re.sub(r"\s+squad", "", t.get_text(), flags=re.IGNORECASE).strip() for t in team_headers]
        
        # 2. Extract Playing XI
        xi_headers = soup.find_all("div", string=re.compile(r"Playing XI", re.IGNORECASE))
        for header in xi_headers:
            container = header.find_parent("div", class_="bg-cbWhite")
            if not container: continue
            
            # Usually two columns (w-1/2) for the two teams
            columns = container.select(".w-1\\/2") 
            if len(columns) >= 2 and len(team_names) >= 2:
                for idx, col in enumerate(columns[:2]):
                    t_name = team_names[idx]
                    players = []
                    for a in col.find_all("a", href=re.compile(r"/profiles/")):
                        # Sometimes name is in a nested span
                        name_tag = a.find("span", class_="text-cbTxtPrim") or a
                        name, role = self.parse_player(name_tag.get_text(strip=True))
                        players.append({
                            "name": name,
                            "role": role,
                            "profile": BASE_URL + a.get("href")
                        })
                    
                    if t_name not in squads: squads[t_name] = {"playing_xi": [], "bench": []}
                    squads[t_name]["playing_xi"] = players

        # 3. Extract Bench
        bench_headers = soup.find_all("div", string=re.compile(r"Bench", re.IGNORECASE))
        for header in bench_headers:
            container = header.find_parent("div", class_="bg-cbWhite")
            if not container: continue
            
            columns = container.select(".w-1\\/2")
            if len(columns) >= 2 and len(team_names) >= 2:
                for idx, col in enumerate(columns[:2]):
                    t_name = team_names[idx]
                    if t_name not in squads: continue
                    
                    players = []
                    for a in col.find_all("a", href=re.compile(r"/profiles/")):
                        name, role = self.parse_player(a.get_text(strip=True))
                        players.append({
                            "name": name,
                            "role": role,
                            "profile": BASE_URL + a.get("href")
                        })
                    squads[t_name]["bench"] = players

        return squads

    def scrape_match_squads(self, squads_url):
        soup = self.get_selenium_soup(squads_url)
        squads = self.extract_squads_from_soup(soup)
        
        # Extract basic metadata from the same page if available
        metadata = {}
        if soup:
            rows = soup.find_all("div", class_="facts-row-grid")
            for r in rows:
                cols = r.find_all("div")
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True).strip(":").strip()
                    val = cols[1].get_text(strip=True)
                    metadata[key] = val
            
            # Fallback for Result if not in facts-row-grid
            if "Result" not in metadata:
                result_div = soup.select_one(".cb-dtl-rt") # Common class for match status on info page
                if result_div:
                    metadata["Result"] = result_div.get_text(strip=True)
        
        return {
            "metadata": metadata,
            
            "squads": squads
        }
