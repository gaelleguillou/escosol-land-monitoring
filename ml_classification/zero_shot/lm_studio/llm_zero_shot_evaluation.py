import argparse
from pprint import pprint

import polars as pl

from .config import LABELS_MAP
from .evaluation import compute_classification_metrics


def main():
    parser = argparse.ArgumentParser(
        description="Compute classification reports for LLM predictions",
    )

    # Required arguments
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the parquet file containing LLM results (from llm_zero_shot_classification_arena.py)",
    )

    args = parser.parse_args()

    # Verify we have all expected score columns
    try:
        df = pl.read_parquet(args.input_file)
        expected_score_cols = [f"{label}_score" for label in LABELS_MAP.values()]
        if not all(col in df.columns for col in expected_score_cols):
            raise ValueError(
                f"Expected score columns {expected_score_cols} not found in parquet file"
            )
    except Exception as e:
        parser.error(f"Input file verification failed: {str(e)}")

    pprint(compute_classification_metrics(df, LABELS_MAP, auto_threshold=True))


if __name__ == "__main__":
    main()
