from django.core.management.base import BaseCommand

from analysis.tasks import process_content_task
from ingestion.parsers.web_stub import WebStubParser


class Command(BaseCommand):
    help = "Queue a mock web ingestion payload for manual testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run ingestion synchronously without Celery.",
        )

    def handle(self, *args, **options):
        parser = WebStubParser()
        ingestion_data = parser.parse()

        if options["sync"]:
            process_content_task(ingestion_data.model_dump())
            self.stdout.write(self.style.SUCCESS("Mock web ingestion completed (sync)."))
            return

        process_content_task.delay(ingestion_data.model_dump())
        self.stdout.write(self.style.SUCCESS("Mock web ingestion queued."))
