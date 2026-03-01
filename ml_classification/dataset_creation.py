import argparse
import re
from pathlib import Path

import polars as pl
from tqdm import tqdm

from .utils import get_raw_text_pymupdf


def clean_text(raw_test: str) -> str:
    text = raw_test.replace("\xa0", " ")
    text = text.replace("\x0c", " ")
    text = text.replace("\n", " ")
    ## Deletes duplicates whitesapces
    text = re.sub(r" {2,}", " ", text)
    return text


def extract_text(pdf_path: Path) -> str | None:
    if not pdf_path.exists():
        return None
    raw_text = get_raw_text_pymupdf(pdf_path)

    return clean_text(raw_text)


def extract_context_index_positions(
    ref_text_clean: str, contexts: list[str]
) -> list[tuple[int, int]]:
    if ref_text_clean is None:
        return None

    res = []

    for context in contexts:
        start_index = ref_text_clean.index(context.strip())
        if start_index is None:
            raise Exception(f"{context} not found in {ref_text_clean}")

        res.append((start_index, len(context)))

    return res


def create_dataset(
    pdf_dir: Path, output_filepath: Path, pdfs_labels_df: pl.DataFrame | None = None
):
    pdfs_to_select = None
    if pdfs_labels_df is not None:
        pdfs_to_select = pdfs_labels_df.get_column("pdf_name").unique().to_list()

    pdfs_dicts = []
    for pdf_path in tqdm(pdf_dir.glob("*.pdf"), desc="Reading PDFs"):
        pdf_name = pdf_path.name
        if (pdfs_to_select is not None) and (pdf_name not in pdfs_to_select):
            continue

        pdf_text = extract_text(pdf_path)

        pdfs_dicts.append({"pdf_name": pdf_name, "pdf_text": pdf_text})

    preprocessed_pdfs_df = pl.DataFrame(pdfs_dicts)

    if pdfs_labels_df is not None:
        preprocessed_pdfs_df = preprocessed_pdfs_df.join(pdfs_labels_df, on="pdf_name")
        preprocessed_pdfs_df = preprocessed_pdfs_df.with_columns(
            pl.col("context")
            .map_elements(clean_text, return_dtype=pl.String)
            .str.split("[SEP]")
            .alias(
                "contexts"
            ),  # Convert context string into list of cleaned context strings
        )

        preprocessed_pdfs_df = preprocessed_pdfs_df.with_columns(
            pl.struct("pdf_text", "contexts")
            .map_elements(
                lambda x: extract_context_index_positions(x["pdf_text"], x["contexts"]),
                return_dtype=pl.List(pl.List(pl.Int64)),
            )
            .alias(
                "contexts_locations"
            )  # Create a list of tuple containing starting index of context and lengths of the context span.
        )

        preprocessed_pdfs_df = preprocessed_pdfs_df.with_columns(
            pl.col("land_type").str.split(", ").list.sort().alias("labels")
        )

    preprocessed_pdfs_df.filter(pl.col("pdf_text").is_null().not_()).write_parquet(
        output_filepath
    )


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Create a dataset with preprocessed PDFs ready to be fed into the models."
    )

    arg_parser.add_argument(
        "pdf_path", help="Path of the folder containing PDFs to be processed"
    )

    arg_parser.add_argument("output_path", help="Path where to output parquet file.")

    arg_parser.add_argument(
        "--labels_dataset",
        help="CSV dataset containing labels for each PDF. Needed to create a preprocessed file with labels for model training or evaluation.",
    )

    args = arg_parser.parse_args()

    pdfs_labels_df = None
    if (labels_dataset := args.labels_dataset) is not None:
        pdfs_labels_df = pl.read_csv(labels_dataset)

    create_dataset(
        Path(args.pdf_path),
        Path(args.output_path),
        pdfs_labels_df,
    )
