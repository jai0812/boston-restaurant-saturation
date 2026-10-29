"""Selenium-based Yelp scraper (fallback when API quota is unavailable).

Scrapes name, rating, review-count, price tier for Yelp search results in a
Boston neighborhood. Respect Yelp's ToS and rate limits — this is for
one-off research, not production.
"""
from __future__ import annotations
import time
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from config.settings import DATA_RAW


def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,2000")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def scrape_yelp(neighborhood: str, max_pages: int = 3) -> pd.DataFrame:
    rows: list[dict] = []
    driver = build_driver()
    try:
        for page in range(max_pages):
            start = page * 10
            url = (
                f"https://www.yelp.com/search?find_desc=Restaurants"
                f"&find_loc={neighborhood.replace(' ', '+')}%2C+Boston%2C+MA"
                f"&start={start}"
            )
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="serp-ia-card"], h3'))
            )
            time.sleep(2)
            cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="serp-ia-card"]')
            for c in cards:
                try:
                    name = c.find_element(By.CSS_SELECTOR, "h3 a").text
                    link = c.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("href")
                except Exception:
                    continue
                def _safe(sel):
                    try:
                        return c.find_element(By.CSS_SELECTOR, sel).text
                    except Exception:
                        return None
                rows.append({
                    "neighborhood": neighborhood,
                    "name": name,
                    "url": link,
                    "rating": _safe('[aria-label*="star rating"]'),
                    "review_text": _safe('[class*="reviewCount"]'),
                    "price": _safe('[class*="priceRange"]'),
                })
    finally:
        driver.quit()

    df = pd.DataFrame(rows)
    out = DATA_RAW / f"yelp_{neighborhood.lower().replace(' ', '_')}.parquet"
    df.to_parquet(out)
    print(f"wrote {len(df)} yelp rows → {out}")
    return df


if __name__ == "__main__":
    scrape_yelp("Jamaica Plain", max_pages=2)
