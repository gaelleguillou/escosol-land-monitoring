"""
Scraper Guadeloupe - PDFs "voltaïque" (2010-2017)
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.guadeloupe.developpement-durable.gouv.fr"

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
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_year_urls_from_index() -> dict:
    """
    Récupère automatiquement les URLs de chaque année depuis les pages d'index.
    Couvre les deux pages de pagination.
    """
    year_urls = {}
    index_pages = [
        f"{BASE_URL}/annees-2010-a-2022-r1437.html",
        f"{BASE_URL}/annees-2010-a-2022-r1437.html?debut_listearticles=8",
    ]

    for index_url in index_pages:
        print(f"  Récupération de l'index : {index_url}")
        resp = requests.get(index_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
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

        time.sleep(1)

    return year_urls


def contains_voltaique(text: str) -> bool:
    """Vérifie si le texte contient 'voltaïque' ou 'voltaique'
    (insensible à la casse)."""
    pattern = re.compile(r"volta[iï]que", re.IGNORECASE)
    return bool(pattern.search(text))


def find_pdfs_for_year(year: int, url: str, session: requests.Session) -> list:
    """
    Parse la page d'une année et retourne la liste des PDFs
    dont la ligne de tableau contient 'voltaïque'/'voltaique'.
    Retourne une liste de dicts : {label, pdf_url, year}
    """
    full_url = urljoin(BASE_URL, url)
    print(f"\n--- Année {year} : {full_url} ---")

    resp = session.get(full_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    pdfs_found = []

    # Stratégie 1 : chercher dans les lignes de tableau <tr>
    for tr in soup.find_all("tr"):
        row_text = tr.get_text(" ", strip=True)
        if contains_voltaique(row_text):
            for a_tag in tr.find_all("a", href=True):
                href = a_tag["href"]
                if href.lower().endswith(".pdf"):
                    label = a_tag.get_text(strip=True) or href.split("/")[-1]
                    pdf_url = urljoin(BASE_URL, href)
                    pdfs_found.append(
                        {"label": label, "pdf_url": pdf_url, "year": year}
                    )
                    print(f"  [TROUVÉ] {label}")
                    print(f"           {pdf_url}")

    # Stratégie 2 : chercher dans les <li> ou <p> (hors tableaux)
    for tag in soup.find_all(["li", "p", "div"]):
        # Éviter de retraiter les éléments déjà dans un <tr>
        if tag.find_parent("tr"):
            continue
        tag_text = tag.get_text(" ", strip=True)
        if contains_voltaique(tag_text):
            for a_tag in tag.find_all("a", href=True):
                href = a_tag["href"]
                if href.lower().endswith(".pdf"):
                    label = a_tag.get_text(strip=True) or href.split("/")[-1]
                    pdf_url = urljoin(BASE_URL, href)
                    # Dédoublonnage
                    if not any(p["pdf_url"] == pdf_url for p in pdfs_found):
                        pdfs_found.append(
                            {"label": label, "pdf_url": pdf_url, "year": year}
                        )
                        print(f"  [TROUVÉ hors tableau] {label}")
                        print(f"           {pdf_url}")

    if not pdfs_found:
        print(f"  Aucun PDF 'voltaïque' trouvé pour {year}.")

    return pdfs_found


def sanitize_filename(name: str) -> str:
    """Nettoie une chaîne pour en faire un nom de fichier valide."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.strip(". ")
    return name[:150]  # limite de longueur


def download_pdf(pdf_info: dict, session: requests.Session) -> bool:
    """Télécharge un PDF dans le dossier de l'année correspondante."""
    year = pdf_info["year"]
    pdf_url = pdf_info["pdf_url"]
    label = pdf_info["label"]

    year_dir = os.path.join(OUTPUT_DIR, str(year))
    os.makedirs(year_dir, exist_ok=True)

    # Nom de fichier = label nettoyé + extension
    filename = sanitize_filename(label)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    filepath = os.path.join(year_dir, filename)

    if os.path.exists(filepath):
        print(f"  [SKIP] Déjà téléchargé : {filename}")
        return True

    try:
        print(f"  [DL] {filename}")
        resp = session.get(pdf_url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        size_kb = os.path.getsize(filepath) / 1024
        print(f"       → Sauvegardé ({size_kb:.1f} Ko)")
        return True
    except Exception as e:
        print(f"  [ERREUR] Impossible de télécharger {pdf_url} : {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("Scraper DEAL Guadeloupe - PDFs 'voltaïque' (2010-2017)")
    print("=" * 60)

    session = requests.Session()

    # Étape 1 : récupérer automatiquement les URLs des années
    print("\n[1/3] Récupération des URLs des années depuis l'index...")
    year_urls = fetch_year_urls_from_index()

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
        pdfs = find_pdfs_for_year(year, year_urls[year], session)
        all_pdfs.extend(pdfs)
        time.sleep(1)  # politesse envers le serveur

    # Étape 3 : téléchargement
    print(f"\n[3/3] Téléchargement de {len(all_pdfs)} PDF(s) vers '{OUTPUT_DIR}/'...")
    success, fail = 0, 0
    for pdf_info in all_pdfs:
        ok = download_pdf(pdf_info, session)
        if ok:
            success += 1
        else:
            fail += 1
        time.sleep(0.5)

    # Résumé
    print("\n" + "=" * 60)
    print(f"Terminé. {success} PDF(s) téléchargé(s), {fail} échec(s).")
    print(f"Dossier de sortie : {os.path.abspath(OUTPUT_DIR)}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
