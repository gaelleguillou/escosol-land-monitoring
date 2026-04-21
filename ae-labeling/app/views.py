from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from sklearn.metrics import classification_report

from .models import Document


@login_required
def labeling_view(request):
    """Main view - shows next available document or handles validation"""

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

        # Verify this user has the lock before allowing save
        if doc.is_locked() and doc.locked_by != request.user:
            return render(
                request,
                "labeling.html",
                {
                    "doc": None,
                    "error": f"Document is being validated by {doc.locked_by.username}",
                },
            )

        doc.validated_predictions = validated_preds
        doc.is_validated = True
        doc.validated_by = request.user
        doc.validated_at = timezone.now()
        doc.save()

        # Release the lock (unlock will set locked_by to None)
        doc.unlock()

        # Redirect to next unvalidated document
        return redirect("labeling")

    # If GET, first release any existing lock held by this user
    existing_locked_docs = Document.objects.filter(locked_by=request.user).all()
    for doc in existing_locked_docs:
        doc.unlock()  # Release previous lock before getting new one

    next_doc = Document.get_next_unlocked_document()

    if not next_doc:
        return render(request, "labeling.html", {"doc": None})

    # Try to acquire lock on this document
    success, _ = next_doc.lock(request.user)

    if not success:
        # If we couldn't lock it, try to find another one
        # This handles the race condition where two users clicked at same time
        return redirect("labeling")  # Refresh and try again

    return render(request, "labeling.html", {"doc": next_doc})


@login_required
def labeling_document_view(request, doc_id):
    """View for accessing a specific document by ID (for admin/re-labeling)"""

    # If POST, save the validation
    if request.method == "POST":
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
        doc.validated_at = timezone.now()

        doc.save()

        # Redirect to next unvalidated document or back to admin
        next_unvalidated = Document.get_next_unlocked_document()
        if next_unvalidated:
            return redirect("labeling_document", doc_id=next_unvalidated.id)
        else:
            return redirect("admin:app_document_changelist")

    # If GET, get the specific document by ID, not checking the lock as we are in case of admin access
    doc = get_object_or_404(Document, id=doc_id)

    return render(request, "labeling.html", {"doc": doc})


@login_required
def skip_document_undelivered_view(request, doc_id):
    """
    View to intentionally skip a document.
    Unlocks the current document and redirects to the next available one.
    """
    doc = get_object_or_404(Document, id=doc_id)

    # Only allow the user who has the lock to skip it
    if doc.locked_by and doc.locked_by == request.user:
        doc.unlock()
        return JsonResponse({"success": True})

    return JsonResponse(
        {"error": "You do not have the lock for this document"}, status=403
    )


@login_required
def release_lock_view(request):
    """API endpoint to manually release a lock (e.g., user closes browser)"""

    if request.method == "POST":
        doc_id = request.POST.get("doc_id")
        doc = get_object_or_404(Document, id=doc_id)

        # Only allow the user who has the lock to release it
        if doc.locked_by and doc.locked_by == request.user:
            doc.unlock()
            return JsonResponse({"success": True})

    return JsonResponse({"error": "Cannot release this lock"}, status=403)


@login_required
def check_lock_status(request, doc_id):
    """API endpoint to check if a document is locked"""

    doc = get_object_or_404(Document, id=doc_id)

    return JsonResponse(
        {
            "is_locked": doc.is_locked(),
            "locked_by": doc.locked_by.username if doc.locked_by else None,
            "locked_at": doc.locked_at.isoformat() if doc.locked_at else None,
        }
    )


@login_required
def dashboard_view(request):
    """View to show statistics and classification report"""
    total_docs = Document.objects.count()
    validated_docs = Document.objects.filter(is_validated=True).count()
    overall_completion = (validated_docs / total_docs * 100) if total_docs > 0 else 0

    # User specific stats
    user_validated_docs = Document.objects.filter(
        validated_by=request.user, is_validated=True
    ).count()

    user_contribution = (
        (user_validated_docs / validated_docs * 100) if validated_docs > 0 else 0
    )

    # User stats table data
    user_stats = (
        Document.objects.filter(is_validated=True)
        .values("validated_by__username")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Classification Report logic

    LABELS_MAP = {
        "Surfaces artificialisées": "surfaces_artificialisees",
        "Surfaces naturelles": "surfaces_naturelles",
        "Surfaces agricoles": "surfaces_agricoles",
        "Surfaces forestières": "surfaces_forestieres",
    }

    true_labels = []
    pred_labels = []
    for doc in Document.objects.filter(is_validated=True):
        validated_preds = []
        model_labels = []
        for human_readable_label, label in LABELS_MAP.items():
            validated_preds.append(doc.validated_predictions.get(label))
            model_labels.append(doc.original_predictions.get(label).get("pred"))
        true_labels.append(validated_preds)
        pred_labels.append(model_labels)

    # Prepare report data: list of dicts with label and count
    classification_report_dict: dict = classification_report(
        true_labels, pred_labels, target_names=LABELS_MAP.keys(), output_dict=True
    )
    # Django doesn't like hyphens :
    sanitized_report = {}
    for key, value in classification_report_dict.items():
        new_key = key.replace(" ", "_")
        if isinstance(value, dict):
            # Also sanitize inner keys (like 'f1-score' -> 'f1_score')
            inner_dict = {}
            for k, v in value.items():
                inner_k = k.replace("-", "_").replace(" ", "_")
                inner_dict[inner_k] = v
            sanitized_report[new_key] = inner_dict
        else:
            sanitized_report[new_key] = value
    context = {
        "total_docs": total_docs,
        "validated_docs": validated_docs,
        "overall_completion": overall_completion,
        "user_validated_docs": user_validated_docs,
        "user_contribution": user_contribution,
        "user_stats": user_stats,
        "classification_report": sanitized_report,
    }

    return render(request, "dashboard.html", context)
