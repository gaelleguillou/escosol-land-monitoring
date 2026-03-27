"""
Module containing utilities to scrape Nord-Pas-de-Calais AE archive website
(https://www.guyane.developpement-durable.gouv.fr/avis-de-l-autorite-environnementale-r852.html)
and extract relevant AE metadata and PDFs.
"""

import asyncio
import locale
import logging
import os
from datetime import datetime
from argparse import ArgumentParser
from pathlib import Path
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from ..config import HEADERS, RETRY_TRANSPORT, TIMEOUT_CONFIG
from ..utils import (
    download_pdfs,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://www.hauts-de-france.developpement-durable.gouv.fr/-Consultation-des-avis-examens-au-cas-par-cas-et-decisions-.html?recherche=photovoltaique%20solaire%20agrivoltaique%20agri-voltaique&departement[]=&communes[]="


async def get_npdc_archive_pdf_urls_and_metadata() -> pd.DataFrame:
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

    docs = []

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=TIMEOUT_CONFIG,
        follow_redirects=True,
        transport=RETRY_TRANSPORT,
    ) as client:
        res = await client.get(ARCHIVE_URL)
        soup = BeautifulSoup(res.text, "html.parser")

        num_docs = int(
            soup.find("div", class_="nb_resultat fr-col-md-6")
            .find("strong")
            .get_text(strip=True)
        )
        next_page_start = 10

        while (next_page_start - 10) < num_docs:
            doc_divs = soup.find_all("div", class_="texte fr-col-md-9")

            for div in doc_divs:
                link_e = div.find("a")
                if link_e is None:
                    continue

                document_title = link_e.get_text(strip=True)
                if not any(
                    e in document_title.lower() for e in ["cas par cas", "avis"]
                ):
                    continue

                a_href = link_e.get("href")
                if a_href is None:
                    continue

                communes_names = None
                communes_names_div = div.find("div", class_="liste_communes")
                if communes_names_div is not None:
                    communes_names = communes_names_div.get_text(strip=True).split("/")

                publish_date = None
                publish_date_div = div.find("div", class_="informations")
                if publish_date_div is not None:
                    publish_date_raw = (
                        publish_date_div.contents[2].strip().replace("1er", "1")
                    )
                    try:
                        publish_date = datetime.strptime(publish_date_raw, "%d %B %Y")
                    except Exception as e:
                        logger.debug("Date can be parsed : %s, %s", publish_date_raw, e)

                pdf_filename = Path(a_href).name
                pdf_url = urljoin(ARCHIVE_URL, a_href)

                docs.append(
                    {
                        "project_name": document_title,
                        "publish_date_scraped": publish_date,
                        "communes_names_scraped": communes_names,
                        "pdf_filename": pdf_filename,
                        "pdf_url": pdf_url,
                    }
                )

            next_page_url = ARCHIVE_URL + f"&debut_articles={next_page_start}"
            next_page_start += 10
            res = await client.get(next_page_url)
            soup = BeautifulSoup(res.text, "html.parser")

    return pd.DataFrame(docs)


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        description="Program that scrapes the URLs of Nord-Pas-de-Calais's MRAe archive website pages that list PDFs of AE."
        "Output a new CSV file _npdc_archive_pdf_links.csv and downloads the PDF files."
    )
    arg_parser.add_argument(
        "-o",
        "--output_path",
        help="Path where to output the resulting _npdc_archive_pdf_links.csv file and downloaded PDFs files."
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

    df = asyncio.run(get_npdc_archive_pdf_urls_and_metadata())
    df.to_csv(output_path / "_npdc_archive_pdf_links.csv", index=False)

    asyncio.run(download_pdfs(df, output_path=output_path))
