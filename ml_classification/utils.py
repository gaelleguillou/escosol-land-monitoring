from pathlib import Path

import numpy as np
import pymupdf


def get_raw_text_pymupdf(path: Path) -> str:
    """
    Extract raw text from a PDF using pymupdf.
    Much faster processing but lower-quality output compared to markdown.
    """
    with pymupdf.open(path) as doc:
        all_texts = [page.get_text() for page in doc]
        text = r"\n".join(all_texts)
        return text


def compute_metrics(metric, eval_pred):
    logits, labels = eval_pred
    # convert the logits to their predicted class
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)
