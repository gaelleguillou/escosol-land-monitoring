import polars as pl
from django.core.management.base import BaseCommand
from app.models import Document

from django.conf import settings


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

        cols_to_get = [e + "_pred" for e in label_names] + [
            e + "_score" for e in label_names
        ]

        df = df.with_columns(pl.struct(cols_to_get).alias("original_predictions"))

        created_count = 0
        skipped_count = 0
        for row in df.iter_rows(named=True):
            # Check if document already exists
            doc, created = Document.objects.get_or_create(
                pdf_name=row["pdf_name"],
                defaults={
                    "pdf_text": str(
                        row["pdf_text"]
                    ),  # There is NULL bytes in the texts
                    "pdf_text_raw": str(row["pdf_text_raw"]).replace(
                        "\x00", ""
                    ),  # There is NULL bytes in the texts
                    "contexts": row.get("contexts", []),
                    "explanation": str(row.get("explanation", "")),
                    "prediction_time": float(row.get("prediction_time", 0)),
                    "original_predictions": row.get("original_predictions", {}),
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1
            doc.save()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {created_count} documents.")
        )
        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Skipped {skipped_count} existing documents.")
            )
