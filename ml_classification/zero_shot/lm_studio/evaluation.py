import logging

import numpy as np
import polars as pl
from sklearn.metrics import classification_report, f1_score


logging.basicConfig()
logger = logging.getLogger(__file__)


def compute_classification_metrics(
    result_df: pl.DataFrame, labels_map: dict[str, str], auto_threshold: bool = False
) -> dict:
    """
    Compute classification metrics for LLM zero-shot predictions.

    This function evaluates model performance by comparing predicted scores
    against true labels. It supports both fixed (0.5) and adaptive thresholding
    for classification decision boundaries. Automatically computes the
    optimal threshold when auto_threshold=True via F1-score maximization.

    Parameters
    ----------
    result_df : polars.DataFrame
        DataFrame containing prediction results with columns:
            * Raw score predictions for each label (e.g., "land_type_A_score")
            * True labels in original format
            * Optional prediction_time column

    auto_threshold : bool, optional
        If True, automatically computes optimal threshold based on F1-score.
        Defaults to False (fixed threshold of 0.5).

    Returns
    -------
    dict
        Classification report containing:
            * Standard classification metrics (precision, recall, f1_score)
            * threshold used
            * Confusion matrix breakdown
            * Computed prediction times statistics

    Notes
    -----
    - Uses scikit-learn's `classification_report` for output generation
    - Implements threshold adaptation by evaluating all 0.5-step increments between
      0 and 1 when auto_threshold=True
    """
    true_labels = result_df.select(*labels_map.values()).to_numpy()

    pred_scores = result_df.select(
        [v + "_score" for v in labels_map.values()]
    ).to_numpy()

    threshold = 0.5
    if auto_threshold:
        logger.info("Finding best threshold")
        best_f1_score = 0

        for threshold_candidate in np.arange(0, 1, 0.05):
            pred_labels = (pred_scores > threshold_candidate).astype(int)
            f1 = f1_score(true_labels, pred_labels, average="micro")
            if f1 > best_f1_score:
                best_f1_score = f1
                threshold = threshold_candidate

        logger.info(
            "Found best threshold : {} with f1_score {}", threshold, best_f1_score
        )

    pred_labels = (pred_scores > threshold).astype(int)

    report: dict = classification_report(
        true_labels, pred_labels, target_names=labels_map.keys(), output_dict=True
    )

    report["prediction_time"] = {
        "total": result_df.select(pl.col("prediction_time").sum()).item(),
        "avg": result_df.select(pl.col("prediction_time").mean()).item(),
        "std": result_df.select(pl.col("prediction_time").std()).item(),
    }

    report["threshold"] = float(threshold)

    return report
