from django.core.management.base import BaseCommand
from ingestion.parsers.web_stub import WebScheduleStubParser
from analysis.tasks import process_content_task

class Command(BaseCommand):
    help = 'Trigger a mock web ingestion event'

    def handle(self, *args, **options):
        parser = WebScheduleStubParser()
        raw_content = parser.fetch("http://mock-url.com")
        ingestion_data = parser.parse(raw_content, url="http://mock-url.com")

        self.stdout.write(self.style.SUCCESS(f"Generated Ingestion Data: {ingestion_data}"))

        # Dispatch to Celery
        process_content_task.delay(ingestion_data.model_dump())
        self.stdout.write(self.style.SUCCESS("Dispatched to AI analysis task."))
