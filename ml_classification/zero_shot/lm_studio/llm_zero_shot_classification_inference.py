import argparse
from datetime import datetime
import logging
import os
from pathlib import Path

import polars as pl
from tqdm import tqdm

from ...dataset_creation import extract_text
from .config import (
    MODELS_CONFIG,
    LABELS,
    LABELS_MAP,
    LLM_OUTPUT_JSON_SCHEMA,
)
from .lm_studio import get_model, run_inference

logging.basicConfig()

logger = logging.getLogger(__file__)


def run_pdfs_inference(
    model_id: str, model_config: dict, pdf_df: pl.DataFrame, system_prompt: str
) -> pl.DataFrame:
    model = get_model(model_id, model_config["model_config"])

    result = []
    for row in tqdm(
        pdf_df.iter_rows(named=True),
        desc=f"Predicting with {model_id}",
        total=len(pdf_df),
    ):
        try:
            res_dict = run_inference(
                model,
                system_prompt=system_prompt,
                pdf_text=row["pdf_text"],
                response_format=LLM_OUTPUT_JSON_SCHEMA,
                labels=LABELS,
                labels_mapping=LABELS_MAP,
            )
        except Exception as e:
            logger.error("Error when running inference of PDF : {}.", row["pdf_name"])
            logger.error(e)
            failed_run_parquet_filepath = (
                Path(os.getcwd()).absolute()
                / f"llm_zero_shot_inference_failed_run_{datetime.now()}.parquet"
            )
            logger.error(
                "Writing already processed PDFS to {}",
                str(failed_run_parquet_filepath),
            )
            pl.DataFrame(result).write_parquet(failed_run_parquet_filepath)
            raise e

        res_dict["pdf_name"] = row["pdf_name"]
        result.append(res_dict)

    result_df = pl.DataFrame(result)

    model.unload()

    return result_df


def create_pdf_df(
    pdfs_path: Path, pdfs_to_skip: list[str] | None = None
) -> pl.DataFrame:
    res = []

    for pdf_path in tqdm(pdfs_path.glob("*.pdf")):
        pdf_name = pdf_path.name

        if (pdfs_to_skip is not None) and (pdf_name in pdfs_to_skip):
            continue

        text = extract_text(pdf_path)

        res.append({"pdf_name": pdf_name, "pdf_text": text})

    return pl.DataFrame(res)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        "lm_studio_zero_shot_inference",
        description="Run inference using ML studio model API and given preprocessed PDF parquet file and prompt",
    )

    arg_parser.add_argument(
        "pdfs_path",
        help="Path of the pdf file to run inference on.",
    )

    arg_parser.add_argument(
        "result_output_filepath",
        help="File path where to store the parquet file containing inference result."
        "If directory does not exists, it will be created",
    )

    arg_parser.add_argument(
        "--resume",
        help="If result_output_filepath points to an existing file, resume inference using it.",
        default=False,
        action="store_true",
    )

    arg_parser.add_argument(
        "--model_id",
        help="Identifier of the model to use. Default: mistralai/ministral-3-3b-instruct-2512",
        default="mistralai/ministral-3-3b-instruct-2512",
    )

    args = arg_parser.parse_args()

    output_df = None

    pdfs_already_processed = []
    if args.resume:
        result_output_filepath = Path(args.result_output_filepath)
        if not result_output_filepath.exists():
            raise Exception(
                f"--resume option selected but {result_output_filepath} does not exists."
            )

        output_df = pl.read_parquet(result_output_filepath)
        pdfs_already_processed = output_df.get_column("pdf_name").unique().to_list()

    pdf_df = create_pdf_df(Path(args.pdfs_path), pdfs_already_processed)
    system_prompt = (Path(__file__).parent / "prompt.md").read_text()

    model_id = args.model_id
    model_config = MODELS_CONFIG[model_id]
    result_df = run_pdfs_inference(model_id, model_config, pdf_df, system_prompt)

    if args.resume and output_df is not None:
        result_df = pl.concat([output_df, result_df])

    result_df.write_parquet(
        Path(args.result_output_filepath),
        mkdir=True,
    )
