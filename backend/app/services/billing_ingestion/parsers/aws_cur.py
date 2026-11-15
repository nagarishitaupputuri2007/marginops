"""AWS Cost and Usage Report (CUR) format parser adapter."""
from typing import List, TextIO
from app.services.billing_ingestion.models import IngestionReport
from app.services.billing_ingestion.parsers.base import BaseBillingParser

AWS_CUR_SIGNATURE_COLUMNS = {
    "lineitem/usagestartdate",
    "lineitem/productcode",
    "lineitem/unblendedcost",
    "pricing/currency",
}


class AWSCURBillingParser(BaseBillingParser):
    """Parser adapter for native AWS Cost and Usage Reports (CUR)."""

    @property
    def parser_name(self) -> str:
        return "aws_cur"

    def can_parse(self, header_row: List[str]) -> bool:
        """Identifies AWS CUR headers."""
        header_set = {col.strip().lower() for col in header_row if col}
        return AWS_CUR_SIGNATURE_COLUMNS.issubset(header_set)

    def parse(self, stream: TextIO) -> IngestionReport:
        """Parses AWS CUR stream into normalized ParsedBillingRecord items."""
        # Adapter placeholder for native AWS CUR format transformation
        report = IngestionReport()
        return report
