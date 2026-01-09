from abc import ABC, abstractmethod
from typing import List, Dict, Any
from analysis.schemas import IngestionData

class BaseParser(ABC):
    """
    Abstract base class for all content parsers.
    """

    @abstractmethod
    def fetch(self, source: str) -> str:
        """
        Fetches raw content from the source.
        """
        pass

    @abstractmethod
    def parse(self, raw_content: str, **kwargs) -> IngestionData:
        """
        Parses raw content into standardized IngestionData.
        """
        pass
