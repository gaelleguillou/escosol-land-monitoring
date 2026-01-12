import httpx
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tqdm import tqdm


def get_pdf_metadata(base_url=None):
    """
    Récupère les métadonnées des PDF liés aux encadrés
    contenant les mots-clés "photovoltaïque" ou "photovoltaique"
    sur les pages avis de recherche par année.

    :param base_url: url de la page d'avis de recherche région x année MRAE
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    results = []
    timeout_config = httpx.Timeout(60.0, connect=10.0)

    with httpx.Client(
        headers=headers, follow_redirects=True, timeout=timeout_config
    ) as client:
        response = client.get(base_url)
        soup = BeautifulSoup(response.text, "html.parser")

        encadres = soup.select("div.texteencadre-spip")
        for div in encadres:
            texte_complet = (
                div.get_text(" ", strip=True).lower().replace("ï", "i")
            )  # Normalisation des caractères, + efficace que chercher par accent

            if "voltaique" in texte_complet:
                strong_tag = div.find("strong")
                titre = strong_tag.get_text(strip=True) if strong_tag else "Sans titre"

                pdf_link = div.select_one("a.fr-download__link")
                if pdf_link and pdf_link.get("href"):
                    pdf_url = urljoin(base_url, pdf_link["href"])
                    pdf_name = pdf_url.split("/")[-1]

                    results.append(
                        {
                            "year_url": base_url,
                            "title": titre,
                            "description": texte_complet,
                            "pdf_link": pdf_url,
                            "pdf_name": pdf_name,
                        }
                    )

    if results:
        return results


if __name__ == "__main__":
    results = []
    year_links = pd.read_csv("data/ae_year_links.csv")
    for _, row in tqdm(year_links.iterrows()):
        data = get_pdf_metadata(row["year_url"])
        if data:
            results.extend(data)
        else:
            print(f"No PDF found for {row['year_url']}")
    df_results = pd.DataFrame(results)
    df_results.columns = ["year_url", "title", "description", "pdf_link", "pdf_name"]
    df_results.to_csv("data/metadata_pdfs.csv", index=False)
