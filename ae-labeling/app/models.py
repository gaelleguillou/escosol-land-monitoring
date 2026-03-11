from datetime import timedelta
from typing import Self

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


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

    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_documents",  # Allows querying documents locked by a user
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.pdf_name

    def is_locked(self) -> bool:
        """Check if document is currently locked. Can release old locks."""

        # Check if the document has been locked more than one hour ago
        if (self.locked_by is not None) and (self.locked_at is not None):
            if timezone.now() - self.locked_at >= timedelta(hours=1):
                self.unlock()
                return False
            return True

        return False

    def lock(self, user) -> tuple[bool, str]:
        """Acquire a lock on this document"""
        # Only allow locking unvalidated documents
        if self.is_validated:
            return False, "Document already validated"

        # Check if already locked by someone else
        if self.is_locked() and (self.locked_by != user):
            return False, f"Document is being validated by {self.locked_by.username}"

        # Lock the document (or refresh lock if same user)
        self.locked_by = user
        self.locked_at = timezone.now()
        self.save(update_fields=["locked_by", "locked_at"])
        return True, "Document locked successfully"

    def unlock(self) -> bool:
        """Release the lock on this document"""
        if self.locked_by:
            self.locked_by = None
            self.locked_at = None
            self.save(update_fields=["locked_by", "locked_at"])
            return True
        return False

    @classmethod
    def get_next_unlocked_document(cls) -> Self | None:
        """Get next document that is not validated and not locked. Release tale locks"""
        LOCK_TIMEOUT = timedelta(minutes=60)  # Lock expires after 10 minutes

        now = timezone.now()

        expired_docs = cls.objects.filter(
            is_validated=False, locked_at__lt=now - LOCK_TIMEOUT
        )

        for expired_doc in expired_docs:
            expired_doc.unlock()  # Release expired lock

        # First try to find truly unlocked documents
        doc = cls.objects.filter(is_validated=False, locked_by=None).first()

        return doc
