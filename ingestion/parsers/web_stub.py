from datetime import datetime, timezone
import uuid

from analysis.schemas import IngestionData
from .base import BaseParser


class WebStubParser(BaseParser):
    """
    Mock parser that returns static content for manual testing.
    """
    source_type = "web_schedule"

    def parse(self) -> IngestionData:
        sample_text = (
            "Course schedule update: Lecture on Monday at 10:00. "
            "Homework deadline: submit lab report by next Friday. "
            "Resources: https://example.com/syllabus"
        )
        return IngestionData(
            text=sample_text,
            source_type=self.source_type,
            source_id=f"web_stub:{uuid.uuid4()}",
            metadata={
                "source_name": "Mock Web Schedule",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
        )
