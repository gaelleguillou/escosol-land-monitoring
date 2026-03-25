"""
Module containing utilities to scrape Somme AE archive website
(https://www.guyane.developpement-durable.gouv.fr/avis-de-l-autorite-environnementale-r852.html)
and extract relevant AE metadata and PDFs.
"""

import asyncio
import logging
import os
import re
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import locale

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from .config import HEADERS, RETRY_TRANSPORT, TIMEOUT_CONFIG
from .utils import download_pdfs, extract_departement_code, extract_commune_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://www.somme.gouv.fr/Actions-de-l-Etat/Environnement/Autorite-environnementale-Avis-sur-les-evaluations-environnementales/Annees-2011-2012-et-2013#Ann%C3%A9e%202011"


async def get_somme_archive_pdf_urls_and_metadata() -> pd.DataFrame:
    """Extract AE PDF links and metadata from Guyane archive website.

    Scrapes the Bretagne AE archive to find relevant AEs,
    extracting project names, commune information, departement details, and
    associated PDF document URLs.

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> import asyncio
    >>> df = asyncio.run(get_bretagne_archive_pdf_and_metadata())
    """
    locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")

    avis = []

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=TIMEOUT_CONFIG,
        follow_redirects=True,
        transport=RETRY_TRANSPORT,
    ) as client:
        res = await client.get(ARCHIVE_URL)

        soup = BeautifulSoup(res.text, "html.parser")

        pdf_links = soup.find_all("p", class_="text-justify")

        with logging_redirect_tqdm():
            for e in tqdm(pdf_links, desc="Extracting Somme AE PDFs link"):
                e_text = e.text.strip().removeprefix("-").removeprefix("•").strip()

                if not any(
                    e in e_text.lower()
                    for e in ["solaire", "photovoltaïque", "photovoltaique"]
                ):
                    continue

                a_element = e.find("a")
                pdf_url: str = a_element.get("href")

                if not pdf_url.endswith(".pdf"):
                    res = await client.get(pdf_url)
                    pdf_soup = BeautifulSoup(res.text, "html.parser")
                    pdf_url = urljoin(
                        ARCHIVE_URL,
                        pdf_soup.find("a", class_="fr-link fr-link--download").get(
                            "href"
                        ),
                    )

                document_title, publish_date_str = e_text.split(" - ")
                publish_date = datetime.strptime(publish_date_str, "%d %B %Y")

                departement_code = extract_departement_code(document_title)
                commune_name = extract_commune_name(document_title)

                avis.append(
                    {
                        "project_name": document_title,
                        "publish_date": publish_date,
                        "commune_name": commune_name,
                        "departement_code": departement_code,
                        "pdf_filename": document_title.replace(" ", "_").lower()
                        + ".pdf",
                        "pdf_url": pdf_url,
                    }
                )

    return pd.DataFrame(avis)


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        description="Program that scrapes the URLs of Somme's MRAe archive website pages that list PDFs of AE."
        "Output a new CSV file _somme_archive_pdf_links.csv and downloads the PDF files."
    )
    arg_parser.add_argument(
        "-o",
        "--output_path",
        help="Path where to output the resulting _somme_archive_pdf_links.csv file and downloaded PDFs files."
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

    df = asyncio.run(get_somme_archive_pdf_urls_and_metadata())
    df.to_csv(output_path / "_somme_archive_pdf_links.csv", index=False)

    asyncio.run(download_pdfs(df, output_path=output_path))
