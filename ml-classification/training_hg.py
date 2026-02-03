from pathlib import Path

import pandas as pd
import evaluate
import numpy as np
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from sklearn.model_selection import train_test_split

from utils import get_raw_text_pymupdf
from dataset_helpers import PDFChunkDataset

metric = evaluate.load("accuracy")
MODEL_NAME = "distilbert/distilbert-base-multilingual-cased"


def train_model(pdf_texts: list[str], pdf_labels: list[int]):
    training_args = TrainingArguments(
        output_dir="hg_training",
        eval_strategy="epoch",
        push_to_hub=False,
        num_train_epochs=20,
    )

    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_texts, test_texts, train_labels, test_labels = train_test_split(
        pdf_texts, pdf_labels, test_size=0.2
    )

    train_dataset = PDFChunkDataset(
        train_texts,
        train_labels,
        tokenizer=tokenizer,
        chunking=True,
        max_seq_len=model.config.max_position_embeddings,
    )
    test_dataset = PDFChunkDataset(
        test_texts,
        test_labels,
        tokenizer=tokenizer,
        chunking=True,
        max_seq_len=model.config.max_position_embeddings,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        compute_metrics=compute_metrics,
    )
    trainer.train()


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    # convert the logits to their predicted class
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)


if __name__ == "__main__":
    pdf_path = Path(
        "/Users/luis/projets/escosol/escosol-land-monitoring/ae-scraping/data/downloads_pdf"
    )

    classified_pdf = pd.read_csv(
        "/Users/luis/projets/escosol/escosol-land-monitoring/ml-classification/datasets/labels.csv"
    )

    classified_pdf["is_artifical_surface"] = classified_pdf["land_type"].isin(
        [
            "Surfaces artificialisées",
            "Surfaces artificialisées et agricoles",
            "Surfaces artificialisées et naturelles",
        ]
    )

    pdf_texts = []
    pdf_labels = []
    for i, e in classified_pdf.iterrows():
        pdf_texts.append(get_raw_text_pymupdf(pdf_path / e["pdf_name"]))
        pdf_labels.append(int(e["is_artifical_surface"]))

    train_model(pdf_texts, pdf_labels)
