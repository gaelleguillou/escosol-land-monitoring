from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "pdf_name",
        "is_validated",
        "validated_by",
        "validated_at",
        "get_prediction_summary",
        "labeling_link",  # Add this new column
    ]

    list_filter = ["is_validated", "validated_at"]

    search_fields = ["pdf_name", "contexts"]

    readonly_fields = [
        "pdf_name",
        "pdf_text_raw",
        "explanation",
        "original_predictions_display",
        "validated_predictions_display",
        "prediction_time",
        "validated_by",
        "validated_at",
    ]

    fieldsets = (
        ("Document Info", {"fields": ("pdf_name", "is_validated")}),
        (
            "Validation Details",
            {"fields": ("validated_by", "validated_at", "prediction_time")},
        ),
        (
            "Predictions",
            {
                "fields": (
                    "original_predictions_display",
                    "validated_predictions_display",
                )
            },
        ),
        (
            "Content",
            {"fields": ("pdf_text_raw", "explanation"), "classes": ["collapse"]},
        ),
    )

    def get_prediction_summary(self, obj):
        """Show a summary of validated predictions"""
        if not obj.is_validated:
            return "Not validated"

        true_labels = [k for k, v in obj.validated_predictions.items() if v]
        if true_labels:
            return f"{len(true_labels)} labels: {', '.join(true_labels)}"
        return "No labels selected"

    get_prediction_summary.short_description = "Predictions"

    def labeling_link(self, obj):
        """Create a link to the document's labeling page"""
        url = reverse("labeling_document", kwargs={"doc_id": obj.id})
        if obj.is_validated:
            return format_html(
                '<a href="{}" class="btn btn-sm btn-outline-primary">View/Edit</a>', url
            )
        else:
            return format_html(
                '<a href="{}" class="btn btn-sm btn-success">Label Now</a>', url
            )

    labeling_link.short_description = "Actions"

    def original_predictions_display(self, obj):
        """Display original predictions in a readable format"""
        if not obj.original_predictions:
            return mark_safe("<em>No predictions</em>")

        html = '<table style="width: 100%; border-collapse: collapse; margin-top: 5px;"><tbody>'
        for label, data in obj.original_predictions.items():
            pred = "✓" if data.get("pred") else "✗"
            score = f"{data.get('score', 0):.2f}"
            safe_label = format_html("{}", label)
            html += (
                f'<tr><td style="padding: 4px 8px; border-bottom: 1px solid #ddd;">{safe_label}</td>'
                f'<td style="padding: 4px 8px; border-bottom: 1px solid #ddd;">{pred}</td>'
                f'<td style="padding: 4px 8px; border-bottom: 1px solid #ddd;">{score}</td></tr>'
            )
        html += "</tbody></table>"

        return mark_safe(html)

    original_predictions_display.short_description = "Original Predictions"

    def validated_predictions_display(self, obj):
        """Display validated predictions in a readable format"""
        if not obj.validated_predictions:
            return mark_safe("<em>Not validated</em>")

        html = '<table style="width: 100%; border-collapse: collapse; margin-top: 5px;"><tbody>'
        for label, is_selected in obj.validated_predictions.items():
            status = "✓ Selected" if is_selected else "✗ Not selected"
            safe_label = format_html("{}", label)
            html += (
                f'<tr><td style="padding: 4px 8px; border-bottom: 1px solid #ddd;">{safe_label}</td>'
                f'<td style="padding: 4px 8px; border-bottom: 1px solid #ddd;">{status}</td></tr>'
            )
        html += "</tbody></table>"

        return mark_safe(html)

    validated_predictions_display.short_description = "Validated Predictions"

    def has_add_permission(self, request):
        """Prevent adding documents through admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deleting only if not validated (optional)"""
        if obj and obj.is_validated:
            return False
        return True
