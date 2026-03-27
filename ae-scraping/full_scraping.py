"""
Scrapes
"""

import asyncio
import logging
import os
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from .archive.bretagne import get_bretagne_archive_pdf_urls_and_metadata
from .archive.guadeloupe import get_guadeloupe_archive_pdf_urls_and_metadata
from .archive.guyane import get_guyane_archive_pdf_urls_and_metadata
from .archive.nord_pas_de_calais import get_npdc_archive_pdf_urls_and_metadata
from .archive.side import get_side_archive_pdf_urls_and_metadata
from .archive.somme import get_somme_archive_pdf_urls_and_metadata
from .mrae import get_mrae_pdf_urls_and_metadata
from .utils import download_pdfs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sites_scraping_function_map = {
    "MRAE": get_mrae_pdf_urls_and_metadata,
    "Bretagne": get_bretagne_archive_pdf_urls_and_metadata,
    "Guyane": get_guyane_archive_pdf_urls_and_metadata,
    "Guadeloupe": get_guadeloupe_archive_pdf_urls_and_metadata,
    "Somme": get_somme_archive_pdf_urls_and_metadata,
    "Nord-Pas-de-Calais": get_npdc_archive_pdf_urls_and_metadata,
    "SIDE": get_side_archive_pdf_urls_and_metadata,
}


async def run_all_scraping_functions() -> list[pd.DataFrame]:
    dfs = []
    for site, func in sites_scraping_function_map.items():
        df = await func()
        dfs.append(df)

    return dfs


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        description="Program that scrapes the URLs of ALL MRAe and archive websites pages to get all relevant AEs."
        "Output a new CSV file _pdfs_metadata.csv and downloads the PDF files."
        "use --metadata-only or --metadata-filepath options to skip parts of the process.",
    )
    arg_parser.add_argument(
        "--metadata-only",
        help="Use this option to only create the CSV files containing the PDF URLs and metadata and avoid downloading all PDFs.",
        action="store_true",
        dest="metadata_only",
    )
    arg_parser.add_argument(
        "--metadata-filepath",
        help="Filepath to metadata file _pdfs_metadata.csv."
        "Use this option to download PDFs from already created _pdfs_metadata.csv file and skip scraping part.",
        type=Path,
        dest="metadata_filepath",
    )
    arg_parser.add_argument(
        "-o",
        "--output_path",
        help="Path where to output the resulting _archive_pdf_links.csv file and downloaded PDFs files."
        "Default to current working directory.",
        type=Path,
        dest="output_path",
    )
    arg_parser.add_argument(
        "--verbose", help="Set logging to debug level.", action="store_true"
    )
    args = arg_parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    output_path = Path(os.getcwd())
    if args.output_path is not None:
        output_path = args.output_path

    df = None
    if args.metadata_filepath is not None:
        logger.info("Reading archive metadata CSV files...")
        df = pd.read_csv(args.metadata_filepath)
    else:
        tasks = []
        for site, func in sites_scraping_function_map.items():
            tasks.append(func)

        dfs = asyncio.run(run_all_scraping_functions())

        df = pd.concat(dfs, ignore_index=True, sort=True)
        df.to_csv(output_path / "_pdfs_metadata.csv", index=False)

    if (args.metadata_only is not None) and not args.metadata_only:
        logger.info("Starting PDFs downloading...")
        asyncio.run(download_pdfs(df, output_path))
