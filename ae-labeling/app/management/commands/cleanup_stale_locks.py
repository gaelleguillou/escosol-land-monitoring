from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from app.models import Document


class Command(BaseCommand):
    help = (
        "Release locks that are older than the specified timeout (default: 30 minutes)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Lock timeout in minutes (default: 30)",
        )

    def handle(self, *args, **options):
        # Get all documents locked since more than timeout
        timeout = timedelta(minutes=options["timeout"])

        stale_docs = Document.objects.filter(
            locked_at__lte=timezone.now() - timeout
        ).all()

        unlocked_docs = 0
        for doc in stale_docs:
            doc.unlock()
            unlocked_docs += 1

        print(f"Unlocked {unlocked_docs} documents.")
