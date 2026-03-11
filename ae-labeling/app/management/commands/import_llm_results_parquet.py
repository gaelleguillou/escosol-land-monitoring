import polars as pl
from django.core.management.base import BaseCommand

from app.models import Document


class Command(BaseCommand):
    help = "Imports data from LLM output parquet file into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "parquet_file",
            type=str,
            help="Path to the parquet file (e.g., ./data/myfile.parquet)",
        )

    def handle(self, *args, **options):
        parquet_path = options["parquet_file"]
        self.stdout.write(f"Reading {parquet_path}...")
        df = pl.read_parquet(parquet_path)

        label_names = [
            "surfaces_agricoles",
            "surfaces_artificialisees",
            "surfaces_forestieres",
            "surfaces_naturelles",
        ]

        created_count = 0
        updated_count = 0
        for row in df.iter_rows(named=True):
            # Check if document already exists

            original_predictions = {}
            for label in label_names:
                pred = row.get(f"{label}_pred")
                score = row.get(f"{label}_score")
                original_predictions[label] = {"pred": pred, "score": score}

            doc, updated = Document.objects.update_or_create(
                pdf_name=row["pdf_name"],
                defaults={
                    "pdf_text": str(row["pdf_text"]).replace(
                        "\x00", ""
                    ),  # There is NULL bytes in the texts
                    "pdf_text_raw": row.get("pdf_text_raw", "").replace(
                        "\x00", ""
                    ),  # There is NULL bytes in the texts
                    "contexts": row.get("contexts", []),
                    "explanation": str(row.get("explanation", "")),
                    "prediction_time": float(row.get("prediction_time", 0)),
                    "original_predictions": original_predictions,
                },
            )
            if updated:
                created_count += 1
            else:
                updated_count += 1
            doc.save()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {created_count} documents.")
        )
        if updated_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Updated {updated_count} existing documents.")
            )
