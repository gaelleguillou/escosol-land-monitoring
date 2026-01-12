import os
import time
import random
import requests
import logging
import pandas as pd

CSV_FILE = "data/metadata_pdfs.csv"
COLUMN_NAME = "pdf_link"
OUTPUT_DIR = "data/downloads_pdf"
LOG_FILE = "download_status.log"
TIMEOUT = 15

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

USER_AGENTS = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",  # noqa: E501
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",  # noqa: E501
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",  # noqa: E501
        "Accept": "application/pdf, */*",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",  # noqa: E501
        "Accept": "text/html,application/pdf",
    },
]


def download_pdfs():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    try:
        df = pd.read_csv(CSV_FILE)
        urls = df[COLUMN_NAME].dropna().unique().tolist()
    except Exception as e:
        print(f"Erreur lors de la lecture du CSV : {e}")
        return

    total = len(urls)
    print(f"Lancement : {total} liens uniques à traiter.")

    for i, url in enumerate(urls, 1):
        file_name = str(url).split("/")[-1].split("?")[0]
        if not file_name.lower().endswith(".pdf"):
            file_name += ".pdf"

        file_path = os.path.join(OUTPUT_DIR, file_name)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            continue

        try:
            headers = random.choice(USER_AGENTS)
            headers["Referer"] = "https://www.google.com/"
            response = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            logging.info(f"SUCCÈS: {file_name}")
            print(f"[{i}/{total}] ✅ OK : {file_name}")
            time.sleep(random.uniform(1.5, 4.0))

        except Exception as e:
            logging.error(f"ERREUR sur {url}: {e}")
            print(f"[{i}/{total}] ⚠️ Échec : {url[:30]}...")
            time.sleep(5)


if __name__ == "__main__":
    download_pdfs()
