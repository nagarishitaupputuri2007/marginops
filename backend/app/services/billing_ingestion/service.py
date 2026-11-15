"""Core Billing Ingestion Service managing parser dispatch, stream ingestion, and reporting."""
import csv
import io
from pathlib import Path
from typing import Dict, List, Optional, TextIO, Union

from app.services.billing_ingestion.models import IngestionReport, RowValidationError
from app.services.billing_ingestion.parsers import (
    AWSCURBillingParser,
    AzureBillingParser,
    BaseBillingParser,
    GCPBillingParser,
    NormalizedBillingParser,
)


class BillingIngestionService:
    """Service responsible for ingesting, validating, and normalizing cloud billing datasets."""

    def __init__(self, parsers: Optional[List[BaseBillingParser]] = None):
        self._parsers: Dict[str, BaseBillingParser] = {}

        default_parsers = parsers or [
            NormalizedBillingParser(),
            AWSCURBillingParser(),
            GCPBillingParser(),
            AzureBillingParser(),
        ]
        for p in default_parsers:
            self.register_parser(p)

    def register_parser(self, parser: BaseBillingParser) -> None:
        """Registers a new cloud billing parser in the service."""
        self._parsers[parser.parser_name] = parser

    def get_parser(self, name: str) -> Optional[BaseBillingParser]:
        """Retrieves a registered parser by its unique name."""
        return self._parsers.get(name)

    def detect_parser(self, sample_header: List[str]) -> Optional[BaseBillingParser]:
        """Auto-detects the matching parser based on the CSV header row."""
        for parser in self._parsers.values():
            if parser.can_parse(sample_header):
                return parser
        return None

    def ingest_file(
        self,
        file_path: Union[str, Path],
        parser_name: Optional[str] = None,
        encoding: str = "utf-8",
    ) -> IngestionReport:
        """Ingests a cloud billing CSV file from disk."""
        path = Path(file_path)
        if not path.is_file():
            report = IngestionReport()
            report.errors.append(
                RowValidationError(
                    row_number=0,
                    field="file_path",
                    error=f"File not found: '{file_path}'",
                )
            )
            return report

        with open(path, "r", encoding=encoding, newline="") as f:
            return self.ingest_stream(f, parser_name=parser_name)

    def ingest_string(
        self,
        csv_content: str,
        parser_name: Optional[str] = None,
    ) -> IngestionReport:
        """Ingests raw CSV text from an in-memory string."""
        stream = io.StringIO(csv_content)
        return self.ingest_stream(stream, parser_name=parser_name)

    def ingest_stream(
        self,
        stream: TextIO,
        parser_name: Optional[str] = None,
    ) -> IngestionReport:
        """Ingests a text stream, auto-detecting the parser if not explicitly specified."""
        # Read header to determine appropriate parser
        stream_pos = stream.tell() if stream.seekable() else None

        header_line = stream.readline()
        if not header_line:
            report = IngestionReport()
            report.errors.append(
                RowValidationError(
                    row_number=1,
                    field="header",
                    error="Empty stream or file provided",
                )
            )
            return report

        # Parse header tokens
        sample_reader = csv.reader([header_line])
        try:
            header_row = next(sample_reader)
        except StopIteration:
            header_row = []

        # Rewind stream
        if stream_pos is not None:
            stream.seek(stream_pos)
        else:
            # If not seekable, prepend header_line
            stream = io.StringIO(header_line + stream.read())

        # Select parser
        parser: Optional[BaseBillingParser] = None
        if parser_name:
            parser = self.get_parser(parser_name)
            if not parser:
                report = IngestionReport()
                report.errors.append(
                    RowValidationError(
                        row_number=1,
                        field="parser_name",
                        error=f"Requested parser '{parser_name}' is not registered. Available: {list(self._parsers.keys())}",
                    )
                )
                return report
        else:
            parser = self.detect_parser(header_row)
            if not parser:
                report = IngestionReport()
                report.errors.append(
                    RowValidationError(
                        row_number=1,
                        field="header",
                        error=f"Unable to auto-detect a compatible billing parser for header: {header_row}",
                    )
                )
                return report

        return parser.parse(stream)
