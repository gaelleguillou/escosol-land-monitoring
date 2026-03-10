from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone

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
