"""
Scraper Guadeloupe - PDFs "voltaïque" (2010-2017)
"""

import asyncio
from datetime import datetime
import os
from pathlib import Path
import re
import time
from argparse import ArgumentParser
from urllib.parse import urljoin

import httpx
import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..config import HEADERS, RETRY_TRANSPORT, TIMEOUT_CONFIG
from ..utils import download_pdfs

ARCHIVE_URL = "https://www.guadeloupe.developpement-durable.gouv.fr"

YEAR_URLS = {
    2017: "/2017-a1819.html",
    2016: "/2016-a1420.html",
    2015: "/2015-a1149.html",
    2014: "/2014-a862.html",
    2013: "/2013-a584.html",
    2012: "/2012-a555.html",
    2011: "/2011-a554.html",
    2010: "/2010-a553.html",
}

OUTPUT_DIR = "pdfs_voltaique"


async def fetch_year_urls_from_index(client: httpx.AsyncClient) -> dict:
    """
    Récupère automatiquement les URLs de chaque année depuis les pages d'index.
    Couvre les deux pages de pagination.
    """
    year_urls = {}
    index_pages = [
        f"{ARCHIVE_URL}/annees-2010-a-2022-r1437.html",
        f"{ARCHIVE_URL}/annees-2010-a-2022-r1437.html?debut_listearticles=8",
    ]

    for index_url in index_pages:
        print(f"  Récupération de l'index : {index_url}")
        resp = await client.get(index_url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        for h2 in soup.find_all("h2"):
            a_tag = h2.find("a")
            if not a_tag:
                continue
            year_text = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if year_text.isdigit():
                year = int(year_text)
                if 2010 <= year <= 2017:
                    year_urls[year] = href
                    print(f"    Année {year} → {href}")

    return year_urls


LABEL_PATTERN = re.compile(r"volta[iï]que|solaire", re.IGNORECASE)


def contains_relevant_keyword(text: str) -> bool:
    """Vérifie si le texte contient 'voltaïque' ou 'voltaique' ou 'solaire'
    (insensible à la casse)."""
    return LABEL_PATTERN.search(text) is not None


def extract_date_from_label(label_text: str) -> datetime | None:
    match_o = re.search("[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}", label_text)

    publish_date = None
    if match_o is not None:
        publish_date_raw = match_o.group()
        publish_date = datetime.strptime(publish_date_raw, "%d/%m/%Y")

    return publish_date


async def find_pdfs_for_year(client: httpx.AsyncClient, year: int, url: str) -> list:
    """
    Parse la page d'une année et retourne la liste des PDFs
    dont la ligne de tableau contient 'voltaïque'/'voltaique'.
    Retourne une liste de dicts : {label, pdf_url, year}
    """
    full_url = urljoin(ARCHIVE_URL, url)
    print(f"\n--- Année {year} : {full_url} ---")

    resp = await client.get(full_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")

    pdfs_found = []

    # Stratégie 1 : chercher dans les lignes de tableau <tr>
    for tr in soup.find_all("tr"):
        row_text = tr.get_text(" ", strip=True)

        if contains_relevant_keyword(row_text):
            last_col_e = list(tr.find_all("td"))[-1]
            for a_tag in tr.find_all("a", href=True):
                href = a_tag["href"]
                if href.lower().endswith(".pdf"):
                    label = a_tag.get_text(strip=True) or href.split("/")[-1]

                    project_name_e = last_col_e.contents[0]
                    if isinstance(project_name_e, str):
                        project_name = project_name_e.strip()
                    else:
                        project_name = project_name_e.text.strip()

                    pdf_url = urljoin(ARCHIVE_URL, href)

                    pdf_filename = Path(href).name
                    publish_date = extract_date_from_label(label)

                    pdfs_found.append(
                        {
                            "project_name": project_name,
                            "publish_date_scraped": publish_date,
                            "pdf_filename": pdf_filename,
                            "pdf_url": pdf_url,
                            "year_scraped": year,
                        }
                    )
                    print(f"  [TROUVÉ] {label}")
                    print(f"           {pdf_url}")

    if not pdfs_found:
        print(f"  Aucun PDF 'voltaïque' trouvé pour {year}.")

    return pdfs_found


def sanitize_filename(name: str) -> str:
    """Nettoie une chaîne pour en faire un nom de fichier valide."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.strip(". ")
    return name[:150]  # limite de longueur


async def get_guadeloupe_archive_pdf_urls_and_metadata() -> pd.DataFrame:
    print("=" * 60)
    print("Scraper DEAL Guadeloupe - PDFs 'voltaïque' (2010-2017)")
    print("=" * 60)

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=TIMEOUT_CONFIG,
        follow_redirects=True,
        transport=RETRY_TRANSPORT,
    ) as client:
        # Étape 1 : récupérer automatiquement les URLs des années
        print("\n[1/3] Récupération des URLs des années depuis l'index...")
        year_urls = await fetch_year_urls_from_index(client=client)

        if not year_urls:
            print("ERREUR : Impossible de récupérer les URLs des années.")
            return

        missing = [y for y in range(2010, 2018) if y not in year_urls]
        if missing:
            print(f"\n⚠  URLs non trouvées pour les années : {missing}")
            print("   Vérifiez manuellement la pagination de l'index.")

        # Étape 2 : scraper chaque page d'année
        print("\n[2/3] Recherche des PDFs 'voltaïque' par année...")
        all_pdfs = []
        for year in sorted(year_urls.keys()):
            pdfs = await find_pdfs_for_year(client, year, year_urls[year])
            all_pdfs.extend(pdfs)
            await asyncio.sleep(0.5)

    return pd.DataFrame(all_pdfs)


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        description="Program that scrapes the URLs of Guyane's MRAe archive website pages that list PDFs of AE."
        "Output a new CSV file _guyane_archive_pdf_links.csv and downloads the PDF files."
    )
    arg_parser.add_argument(
        "-o",
        "--output_path",
        help="Path where to output the resulting _guyane_archive_pdf_links.csv file and downloaded PDFs files."
        "Default to current working directory.",
        type=Path,
        dest="output_path",
    )
    args = arg_parser.parse_args()

    output_path = Path(os.getcwd())
    if args.output_path is not None:
        output_path = args.output_path

    if not output_path.exists():
        output_path.mkdir(parents=True)

    df = asyncio.run(get_guadeloupe_archive_pdf_urls_and_metadata())
    df.to_csv(output_path / "_guadeloupe_archive_pdf_links.csv", index=False)

    asyncio.run(download_pdfs(df, output_path=output_path))
