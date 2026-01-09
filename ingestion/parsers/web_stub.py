import datetime
from .base import BaseParser
from analysis.schemas import IngestionData

class WebScheduleStubParser(BaseParser):
    """
    A stub parser simulating fetching a schedule from a university website.
    """

    def fetch(self, source: str) -> str:
        # Simulate an HTTP request
        print(f"Fetching schedule from {source}...")
        return """
        University Schedule Fall 2023
        Course: Advanced AI
        Time: Mondays 10:00 AM
        Location: Room 301
        """

    def parse(self, raw_content: str, **kwargs) -> IngestionData:
        # Simulate parsing logic
        return IngestionData(
            text=raw_content.strip(),
            source_type="web_schedule",
            source_id=f"web_sched_{datetime.date.today()}",
            metadata={
                "url": kwargs.get("url", "http://university.edu/schedule"),
                "fetch_date": str(datetime.date.today())
            }
        )
