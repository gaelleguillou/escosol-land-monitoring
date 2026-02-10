import re
from pathlib import Path

import polars as pl
from utils import get_raw_text_pymupdf


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


def create_dataset(pdf_df: pl.DataFrame, pdf_dir: Path, output_dir: Path):
    pdf_df = pdf_df.with_columns(
        pl.col("pdf_name")
        .map_elements(lambda x: extract_text(pdf_dir / x), return_dtype=pl.String)
        .alias("pdf_text"),  # Extract text from PDF and clean it
        pl.col("context")
        .map_elements(clean_text, return_dtype=pl.String)
        .str.split("[SEP]")
        .alias(
            "contexts"
        ),  # Convert context string into list of cleaned context strings
    )

    pdf_df = pdf_df.with_columns(
        pl.struct("pdf_text", "contexts")
        .map_elements(
            lambda x: extract_context_index_positions(x["pdf_text"], x["contexts"]),
            return_dtype=pl.List(pl.List(pl.Int64)),
        )
        .alias(
            "contexts_locations"
        )  # Create a list of tuple containing starting index of context and lengths of the context span.
    )

    pdf_df = pdf_df.with_columns(
        pl.col("land_type").str.split(", ").list.sort().alias("labels")
    )

    columns_to_take = [
        "pdf_name",
        "context",
        "page",
        "land_type",
        "pdf_text",
        "contexts",
        "contexts_locations",
        "labels",
    ]

    pdf_df.filter(pl.col("pdf_text").is_null().not_()).select(
        columns_to_take
    ).write_parquet(output_dir / "pdf_preprocessed_df.parquet")


if __name__ == "__main__":
    pdf_df = pl.read_csv(
        "/Users/luis/projets/escosol/escosol-land-monitoring/ml-classification/datasets/pdf_with_labels.csv"
    )

    create_dataset(
        pdf_df,
        Path(
            "/Users/luis/projets/escosol/escosol-land-monitoring/ae-scraping/data/downloads_pdf"
        ),
        Path(
            "/Users/luis/projets/escosol/escosol-land-monitoring/ml-classification/datasets"
        ),
    )
