"""
Module containing utilities to scrape Guyane AE archive website
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

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from ..config import HEADERS, RETRY_TRANSPORT, TIMEOUT_CONFIG
from ..utils import download_pdfs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://www.guyane.developpement-durable.gouv.fr/avis-de-l-autorite-environnementale-r852.html"


async def get_guyane_archive_pdf_urls_and_metadata() -> pd.DataFrame:
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
    >>> df = asyncio.run(get_guyane_archive_pdf_urls_and_metadata())
    """

    avis = []

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=TIMEOUT_CONFIG,
        follow_redirects=True,
        transport=RETRY_TRANSPORT,
    ) as client:
        years_links: list[dict] = []
        res = await client.get(ARCHIVE_URL)

        soup = BeautifulSoup(res.text, "html.parser")

        years_a = soup.find_all("a", class_="lien-sous-rubrique fr-link")
        for a in years_a:
            url = a.get("href")
            year = None

            if a.text.strip() == "Avis publiés":
                continue

            year_match = re.search(r"[0-9]{4}", a.text)
            if year_match is not None:
                year = year_match.group(0)

            years_links.append({"url": url, "year": year})

        document_links = []
        with logging_redirect_tqdm():
            for e in tqdm(years_a, desc="Extracting Guyane AE PDFs link"):
                document_page_link = e.get("href")
                res = await client.get(urljoin(ARCHIVE_URL, document_page_link))
                soup = BeautifulSoup(res.text, "html.parser")

                document_links.extend(
                    soup.find_all("a", class_="fr-card__link article-card-lien")
                )
                if soup.find("ul", class_="fr-pagination__list") is not None:
                    next_page_element = soup.find(
                        "a",
                        class_="fr-pagination__link fr-pagination__link--next fr-pagination__link--lg-label",
                    )
                    next_page_href: str | None = next_page_element.get("href")
                    while next_page_href is not None:
                        next_page_link = urljoin(ARCHIVE_URL, next_page_href)
                        res = await client.get(next_page_link)
                        soup = BeautifulSoup(res.text, "html.parser")
                        document_links.extend(
                            soup.find_all("a", class_="fr-card__link article-card-lien")
                        )
                        next_page_element = soup.find(
                            "a",
                            class_="fr-pagination__link fr-pagination__link--next fr-pagination__link--lg-label",
                        )
                        next_page_href: str | None = next_page_element.get("href")

            for doc in document_links:
                doc_title = doc.text

                if not any(
                    e in doc_title.lower().strip()
                    for e in ["solaire", "voltaïque", "voltaique"]
                ):
                    continue

                doc_link = doc.get("href")
                doc_res = await client.get(urljoin(ARCHIVE_URL, doc_link))
                doc_soup = BeautifulSoup(doc_res.text, "html.parser")

                publish_date_e = doc_soup.find("time")
                publish_date = None
                if publish_date_e is not None:
                    publish_date_str = publish_date_e.get("datetime")
                    publish_date = datetime.strptime(publish_date_str, "%Y-%m-%d")

                pdf_e = doc_soup.find("a", class_="fr-download__link")
                pdf_filename = pdf_e.contents[0].strip().replace(" ", "_") + ".pdf"
                pdf_url = urljoin(ARCHIVE_URL, pdf_e.get("href"))

                avis.append(
                    {
                        "project_name": doc_title,
                        "departement_code": "973",
                        "publish_date_scraped": publish_date,
                        "pdf_filename": pdf_filename,
                        "pdf_url": pdf_url,
                    }
                )

    return pd.DataFrame(avis)


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

    df = asyncio.run(get_guyane_archive_pdf_urls_and_metadata())
    df.to_csv(output_path / "_guyane_archive_pdf_links.csv", index=False)

    asyncio.run(download_pdfs(df, output_path=output_path))
