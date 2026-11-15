"""Azure Cost Management export parser adapter."""
from typing import List, TextIO
from app.services.billing_ingestion.models import IngestionReport
from app.services.billing_ingestion.parsers.base import BaseBillingParser

AZURE_SIGNATURE_COLUMNS = {
    "date",
    "metercategory",
    "costinbillingcurrency",
    "billingcurrency",
}


class AzureBillingParser(BaseBillingParser):
    """Parser adapter for native Azure Cost Management CSV exports."""

    @property
    def parser_name(self) -> str:
        return "azure_cost"

    def can_parse(self, header_row: List[str]) -> bool:
        """Identifies Azure Cost Management export headers."""
        header_set = {col.strip().lower() for col in header_row if col}
        return AZURE_SIGNATURE_COLUMNS.issubset(header_set)

    def parse(self, stream: TextIO) -> IngestionReport:
        """Parses Azure export stream into normalized ParsedBillingRecord items."""
        # Adapter placeholder for native Azure export format transformation
        report = IngestionReport()
        return report
