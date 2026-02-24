from pathlib import Path

import evaluate
import pandas as pd
from datasets import Dataset
from setfit import SetFitModel, Trainer, TrainingArguments
from sklearn.model_selection import train_test_split
from utils import get_raw_text_pymupdf

metric = evaluate.load("accuracy")


def train_model(pdf_texts: list[str], pdf_labels: list[int]):
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        pdf_texts, pdf_labels, test_size=0.2
    )

    train_dataset = Dataset.from_dict({"text": train_texts, "label": train_labels})
    test_dataset = Dataset.from_dict({"text": test_texts, "label": test_labels})
    # Initializing a new SetFit model
    model = SetFitModel.from_pretrained(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )

    # Preparing the training arguments
    args = TrainingArguments(
        batch_size=8,
        num_epochs=10,
    )

    # Preparing the trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
    )
    trainer.train()

    trainer.evaluate(test_dataset)


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
