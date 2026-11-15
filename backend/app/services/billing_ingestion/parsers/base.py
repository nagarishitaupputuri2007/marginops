"""Abstract base class for cloud billing data parsers."""
from abc import ABC, abstractmethod
from typing import TextIO
from app.services.billing_ingestion.models import IngestionReport


class BaseBillingParser(ABC):
    """Abstract parser interface for reading cloud billing data exports."""

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Unique identifier for this parser implementation."""
        pass

    @abstractmethod
    def can_parse(self, header_row: list[str]) -> bool:
        """Determines if this parser can process a CSV file based on its header."""
        pass

    @abstractmethod
    def parse(self, stream: TextIO) -> IngestionReport:
        """Parses a text stream and returns an IngestionReport."""
        pass
