import pprint
import time
from datetime import datetime
from pathlib import Path

import lmstudio as lms
import polars as pl
from sklearn.metrics import classification_report
from tqdm import tqdm

MODELS_CONFIG = [
    # {
    #    "model_id": "mistralai/ministral-3-3b-instruct-2512",
    #    "model_config": {
    #        "contextLength": 32768,
    #    },
    # },
    # {
    #    "model_id": "ministral-3-8b-instruct-2512",
    #    "model_config": {
    #        "contextLength": 32768,
    #    },
    # },
    {
        "model_id": "smollm3-3b-mlx",
        "model_config": {
            "contextLength": 32768,
        },
    },
]

output_json_schema = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {
                "Surfaces artificialisées": {"type": "number"},
                "Surfaces naturelles": {"type": "number"},
                "Surfaces agricoles": {"type": "number"},
                "Surfaces forestières": {"type": "number"},
            },
            "required": [
                "Surfaces artificialisées",
                "Surfaces naturelles",
                "Surfaces agricoles",
                "Surfaces forestières",
            ],
        },
        "contexts": {"type": "array", "items": {"type": "string"}},
        "explanation": {"type": "string"},
    },
    "required": ["scores", "contexts", "explanation"],
}

LABELS = [
    "Surfaces artificialisées",
    "Surfaces naturelles",
    "Surfaces agricoles",
    "Surfaces forestières",
]

LABELS_MAP = {
    "Surfaces artificialisées": "surfaces_artificialisees",
    "Surfaces naturelles": "surfaces_naturelles",
    "Surfaces agricoles": "surfaces_agricoles",
    "Surfaces forestières": "surfaces_forestieres",
}

llm_client = lms.get_default_client()


def run_inference(
    model_config: dict, pdf_df: pl.DataFrame, system_prompt: str
) -> pl.DataFrame:
    model = llm_client.llm.load_new_instance(
        model_config["model_id"], config=model_config["model_config"]
    )

    result = []
    for row in tqdm(
        pdf_df.iter_rows(named=True),
        desc=f"Predicting with {model_config['model_id']}",
        total=len(pdf_df),
    ):
        res_dict = {}
        pdf_name = row["pdf_name"]
        res_dict["pdf_name"] = pdf_name
        true_labels = row["land_type"]

        # Init true label matrix
        for label in LABELS:
            res_dict[LABELS_MAP[label]] = 1 if label in true_labels else 0

        pdf_text = row["pdf_text"]

        chat = lms.Chat(system_prompt)
        chat.add_user_message(pdf_text)

        start_time = time.time()
        prediction = model.respond(
            chat, response_format=output_json_schema, config={"temperature": 0.05}
        )

        total_time = time.time() - start_time
        res_dict["prediction_time"] = total_time

        # Create predicted score matrix
        for label, score in prediction.parsed["scores"].items():  # type: ignore
            res_dict[LABELS_MAP[label] + "_score"] = score

        res_dict["contexts"] = prediction.parsed["contexts"]
        res_dict["explanation"] = prediction.parsed["explanation"]

        result.append(res_dict)

    result_df = pl.DataFrame(result)

    model.unload()

    return result_df


def compute_classification_metrics(result_df: pl.DataFrame) -> dict:
    true_labels = result_df.select(*LABELS_MAP.values()).to_numpy()
    pred_scores = result_df.select(
        [v + "_score" for v in LABELS_MAP.values()]
    ).to_numpy()
    pred_labels = (pred_scores > 0.5).astype(int)

    report = classification_report(
        true_labels, pred_labels, target_names=LABELS, output_dict=True
    )

    report["prediction_time"] = {
        "total": result_df.select(pl.col("prediction_time").sum()).item(),
        "avg": result_df.select(pl.col("prediction_time").mean()).item(),
        "std": result_df.select(pl.col("prediction_time").std()).item(),
    }

    return report


if __name__ == "__main__":
    pdf_df = pl.read_parquet("ml-classification/datasets/pdf_preprocessed_df.parquet")
    system_prompt = Path("ml-classification/prompt.md").read_text()

    for config in MODELS_CONFIG:
        result_df = run_inference(config, pdf_df, system_prompt)

        result_df.write_parquet(
            Path("llm_results/")
            / config["model_id"].replace("/", "_")
            / f"{datetime.now():%Y_%m_%d_%H%M}.parquet",
            mkdir=True,
        )

        classification_report_dict = compute_classification_metrics(result_df)

        pprint.pp(classification_report_dict)
