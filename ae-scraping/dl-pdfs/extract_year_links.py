# Access pages and extract links to avis projet x année

import pandas as pd

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


def get_mrae_links(base_url=None, region=None):
    """
    Récupère les liens vers les pages annuelles des avis de projets MRAE
    pour une région donnée.

    :param base_url: url de la page régionale MRAE
    :param region: région
    """
    timeout_config = httpx.Timeout(60.0, connect=10.0)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    all_links = []
    current_url = base_url

    with httpx.Client(
        headers=headers, timeout=timeout_config, follow_redirects=True
    ) as client:
        while current_url:
            response = client.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            links = soup.select("h2.fr-card__title a")
            for a in links:
                full_url = urljoin(base_url, a["href"])
                year = re.search(r"(\d{4})", a["title"]).group(1)
                all_links.append([base_url, region, year, full_url])

            next_page = soup.select_one("a.fr-pagination__link--next")
            if next_page and next_page.get("href"):
                current_url = urljoin(base_url, next_page["href"])
            else:
                current_url = None

    return all_links


if __name__ == "__main__":
    results = []
    region_links = pd.read_csv("data/region_links_ae.csv")
    for _, row in region_links.iterrows():
        data = get_mrae_links(row["site"], row["region"])
        results.extend(data)
    df_results = pd.DataFrame(results)
    df_results.columns = ["base_url", "region", "year", "year_url"]
    df_results.to_csv("data/ae_year_links.csv", index=False)
