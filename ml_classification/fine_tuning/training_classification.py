from pathlib import Path

import lightning as L
import pandas as pd
import torch
from torch.utils.data import DataLoader

from sklearn.model_selection import train_test_split
from utils import get_raw_text_pymupdf
from ml_classification.fine_tuning.dataset_helpers import PDFChunkDataset

from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoConfig

MODEL_NAME = "distilbert/distilbert-base-multilingual-cased"
MAX_LEN = 512
CHUNK_SIZE = 500
STRIDE = 100
BATCH_SIZE = 32
LR = 2e-6
EPOCHS = 10
NUM_LABELS = 2


# ---------- Lightning Module ----------
class DebertaPDFClassifier(L.LightningModule):
    def __init__(self, num_labels=NUM_LABELS, lr=LR):
        super().__init__()
        self.save_hyperparameters()
        self.config = AutoConfig.from_pretrained(MODEL_NAME, num_labels=NUM_LABELS)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME, config=self.config
        )

    def forward(self, **batch):
        return self.model(**batch)

    def training_step(self, batch, batch_idx):
        out = self.model(**batch)
        loss = out.loss
        self.log("train_loss", loss, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        out = self(**batch)
        preds = torch.argmax(out.logits, dim=1)
        labels = batch["labels"]
        acc = (preds == labels).float().mean()
        self.log("val_loss", out.loss, prog_bar=True)
        self.log("val_acc", acc, prog_bar=True)

    def configure_optimizers(self):
        return torch.optim.AdamW(self.parameters(), lr=self.hparams.lr)


# ---------- Train ----------
def train_pdf_classifier(pdf_texts, pdf_labels):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    X_train, X_val, y_train, y_val = train_test_split(
        pdf_texts, pdf_labels, test_size=0.2, stratify=pdf_labels, random_state=42
    )

    train_ds = PDFChunkDataset(X_train, y_train, tokenizer, chunking=True)
    val_ds = PDFChunkDataset(X_val, y_val, tokenizer, chunking=True)

    train_loader = DataLoader(
        train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=4
    )
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, num_workers=4)

    model = DebertaPDFClassifier(num_labels=NUM_LABELS)

    trainer = L.Trainer(
        max_epochs=EPOCHS,
        accelerator="auto",
        devices="auto",
        log_every_n_steps=10,
        precision="32-true",
    )

    trainer.fit(model, train_loader, val_loader)
    return model, tokenizer


# ---------- Example Usage ----------
# model, tokenizer = train_pdf_classifier(pdf_texts, pdf_labels)
# print(predict_pdf(model, tokenizer, pdf_texts[0], label_names))

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

    train_pdf_classifier(pdf_texts, pdf_labels)
