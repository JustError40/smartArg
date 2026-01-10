from abc import ABC, abstractmethod

from analysis.schemas import IngestionData


class BaseParser(ABC):
    """
    Abstract parser for non-Telegram ingestion sources.
    """
    source_type: str = "unknown"

    @abstractmethod
    def parse(self) -> IngestionData:
        raise NotImplementedError
