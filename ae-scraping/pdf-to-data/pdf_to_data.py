import os
import re
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import pymupdf
from tqdm import tqdm

# Code copied from the data4good sufficiency project
# https://github.com/dataforgoodfr/13_democratiser_sobriete
# Which covered similar issues of PDF text extraction


def get_raw_text_pymupdf(path: Path) -> str:
    """
    Extract raw text from a PDF using pymupdf.
    Much faster processing but lower-quality output compared to markdown.
    """
    with pymupdf.open(path) as doc:
        all_texts = [page.get_text() for page in doc]
        text = chr(12).join(all_texts)
        return text


def extract_context(text):
    lignes = text.split("\n")

    pattern_start = r"^\s*([1A])[^a-zA-Z0-9].*(?:présentation|contexte)"

    index_debut = -1
    char_suivant = ""

    for i, ligne in enumerate(lignes):
        if re.search(pattern_start, ligne, re.IGNORECASE):
            index_debut = i
            match = re.search(r"^\s*([1A])", ligne)
            if match:
                char_origine = match.group(1)
                char_suivant = "2" if char_origine == "1" else "B"
                break
            else:
                continue

    if index_debut == -1:
        return text.strip()

    pattern_end = rf"^\s*{char_suivant}[^a-zA-Z0-9]+\s+[a-zA-ZÀ-ÿ]"

    index_fin = -1
    for j in range(index_debut + 1, len(lignes)):
        if re.search(pattern_end, lignes[j]):
            index_fin = j
            break

    paragraphes = (
        lignes[index_debut + 1 : index_fin]  # noqa: E203
        if index_fin != -1
        else lignes[index_debut + 1 :]  # noqa: E203
    )

    return "\n".join(paragraphes).strip()


def extraire_max_hectares(text):
    pattern = r"(\d{1,3}(?:[\s]\d{3})*(?:[.,]\d+)?)\s*(?:ha\b|hectares?\b)"

    matches = re.findall(pattern, text, re.IGNORECASE)

    if not matches:
        return None

    valeurs = []
    for val in matches:
        val_propre = re.sub(r"\s+", "", val).replace(",", ".")
        valeurs.append(float(val_propre))

    return max(valeurs)


def extraire_max_mwc(text):
    pattern = r"(\d{1,3}(?:[\s]\d{3})*(?:[.,]\d+)?)\s*MWc\b"

    matches = re.findall(pattern, text, re.IGNORECASE)

    if not matches:
        return None

    valeurs = []
    for val in matches:
        val_propre = re.sub(r"\s+", "", val).replace(",", ".")
        valeurs.append(float(val_propre))

    return max(valeurs)


def process_all_pdfs(folder_path: Path, output_path: Path):
    """
    Process all PDF files in the specified folder
    and extract land surface and power data then save it as a CSV file in output_path folder.
    """
    headers = ["pdf_name", "land_surface_ha", "power_mwc"]

    results = []
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

    for filename in tqdm(pdf_files):
        try:
            # 1. Extraction texte brut
            raw_text = get_raw_text_pymupdf(folder_path / filename)

            # 2. Extraction du contexte
            contexte = extract_context(raw_text)

            # 3. Extraction des données (priorité contexte, sinon texte brut)
            # Hectares
            ha = extraire_max_hectares(contexte)
            if not ha:
                ha = extraire_max_hectares(raw_text)

            # Puissance
            mwc = extraire_max_mwc(contexte)
            if not mwc:
                mwc = extraire_max_mwc(raw_text)

            data = {"pdf_name": filename, "land_surface_ha": ha, "power_mwc": mwc}

            results.append(data)

        except Exception as e:
            print(f"Erreur sur {filename}: {e}")

    pd.DataFrame(results, columns=headers).to_csv(
        output_path / "pdf_extraction_results.csv", index=False
    )


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        "pdf_to_data",
        description="Extract data from AE PDFs. Result is saved in a file pdf_extraction_result.csv.",
    )
    arg_parser.add_argument(
        "pdf_path",
        help="Path of the folder where are PDFs are located.",
    )

    arg_parser.add_argument(
        "-o",
        "--output_path",
        help="Path of the folder where the CSV containing extracted data will be saved. Default to pdf_path.",
        dest="output_path",
    )

    args = arg_parser.parse_args()
    pdf_path = Path(args.pdf_path)
    output_path = pdf_path
    if args.output_path is not None:
        output_path = Path(args.output_path)

    process_all_pdfs(pdf_path, output_path)
