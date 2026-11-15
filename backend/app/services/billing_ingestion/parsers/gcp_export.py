"""Google Cloud Billing BigQuery export parser adapter."""
from typing import List, TextIO
from app.services.billing_ingestion.models import IngestionReport
from app.services.billing_ingestion.parsers.base import BaseBillingParser

GCP_SIGNATURE_COLUMNS = {
    "usage_start_time",
    "service.description",
    "sku.description",
    "cost",
    "currency",
}


class GCPBillingParser(BaseBillingParser):
    """Parser adapter for native GCP Cloud Billing BigQuery CSV exports."""

    @property
    def parser_name(self) -> str:
        return "gcp_export"

    def can_parse(self, header_row: List[str]) -> bool:
        """Identifies GCP BigQuery billing export headers."""
        header_set = {col.strip().lower() for col in header_row if col}
        return GCP_SIGNATURE_COLUMNS.issubset(header_set)

    def parse(self, stream: TextIO) -> IngestionReport:
        """Parses GCP export stream into normalized ParsedBillingRecord items."""
        # Adapter placeholder for native GCP export format transformation
        report = IngestionReport()
        return report
