from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    # Original Data from Parquet
    pdf_name = models.CharField(max_length=255, unique=True)
    pdf_text = models.TextField()
    pdf_text_raw = models.TextField()
    contexts = models.JSONField(default=list, blank=True)  # List of strings
    explanation = models.TextField(blank=True)
    prediction_time = models.FloatField(null=True, blank=True)

    # Original LLM Predictions (Stored as JSON for flexibility)
    # Structure: {"surfaces_agricoles": {"score": 0.8, "pred": True}, ...}
    original_predictions = models.JSONField(default=dict)

    # Validation Status
    is_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    validated_at = models.DateTimeField(null=True)

    # Corrected Predictions (Stored as JSON)
    # Structure: {"surfaces_agricoles": True, ...}
    validated_predictions = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.pdf_name
