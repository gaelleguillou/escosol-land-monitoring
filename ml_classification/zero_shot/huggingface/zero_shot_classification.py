from pathlib import Path
import statistics

import pandas as pd
from ml_classification.fine_tuning.dataset_helpers import chunk_text
from transformers import AutoTokenizer, pipeline
from utils import get_raw_text_pymupdf

# ---- CONFIG ----
MODEL_NAME = "morit/french_xlm_xnli"
LABELS = [
    "Surfaces agricoles",
    "Surfaces forestières",
    "Surfaces naturelles",
    "Surfaces artificialisées",
]
MAX_CHUNK_TOKENS = 400

# ---- Load pipeline ----
classifier = pipeline(
    "zero-shot-classification",
    model=MODEL_NAME,
    hypothesis_template="Le projet va être implanté sur une surface de type : {}",
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


# ---- Classification d'un document ----
def classify_document_zero_shot(text, labels, top_k=5):
    chunks = chunk_text(tokenizer, text, max_tokens=MAX_CHUNK_TOKENS, stride=0)

    chunk_scores = []

    for chunk in chunks:
        result = classifier(chunk, candidate_labels=labels, multi_label=True)
        scores = dict(zip(result["labels"], result["scores"]))
        chunk_scores.append(scores)

    # ---- Agrégation par mean pooling ----
    agg_scores_mean = {label: 0.0 for label in labels}
    agg_scores_max = {label: 0.0 for label in labels}
    for label in labels:
        agg_scores_mean[label] = statistics.mean(score[label] for score in chunk_scores)
        agg_scores_max[label] = max(score[label] for score in chunk_scores)
    return agg_scores_mean, agg_scores_max, chunk_scores


# ---- Exemple d'utilisation ----
if __name__ == "__main__":
    pdf_path = Path(
        "/Users/luis/projets/escosol/escosol-land-monitoring/ae-scraping/data/downloads_pdf"
    )

    classified_pdf = pd.read_csv(
        "/Users/luis/projets/escosol/escosol-land-monitoring/ml-classification/datasets/pdf_with_labels.csv"
    )

    result = {}
    for i, e in classified_pdf.iterrows():
        path = pdf_path / e["pdf_name"]
        if not path.exists():
            continue
        text = get_raw_text_pymupdf(path)
        true_labels = e["land_type"].split(", ")

        agg_scores_mean, agg_scores_max, all_chunk_scores = classify_document_zero_shot(
            text, LABELS
        )

        print("\n=== Scores document ===")
        print(e["pdf_name"])
        print(f"labels : {true_labels}")
        print("------mean------")
        for label, score in agg_scores_mean.items():
            print(f"{label:10s} : {score:.4f}")
        print("------max------")
        for label, score in agg_scores_max.items():
            print(f"{label:10s} : {score:.4f}")
