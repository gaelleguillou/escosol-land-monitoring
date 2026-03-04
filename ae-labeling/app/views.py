from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings

from .models import Document


@login_required
def labeling_view(request):
    # If POST, save the validation
    if request.method == "POST":
        doc_id = request.POST.get("doc_id")
        validated_preds = {}

        # The 4 labels
        labels = settings.AE_LABELS

        for label in labels:
            # Check if the checkbox was sent in form (value="on")
            validated_preds[label] = request.POST.get(label) == "on"

        doc = get_object_or_404(Document, id=doc_id)
        doc.validated_predictions = validated_preds
        doc.is_validated = True
        doc.validated_by = request.user
        doc.save()

        # Redirect to next
        return redirect("labeling")

    # If GET, find next unvalidated document
    # We filter by is_validated=False. If none left, show empty state.
    next_doc = Document.objects.filter(is_validated=False).first()

    if not next_doc:
        return render(request, "labeling.html", {"doc": None})

    return render(request, "labeling.html", {"doc": next_doc})
