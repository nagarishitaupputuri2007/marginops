"""Parser for MarginOps normalized multi-cloud billing CSV exports."""
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from typing import Dict, List, Optional, Set, TextIO

from app.services.billing_ingestion.models import (
    IngestionReport,
    ParsedBillingRecord,
    RowValidationError,
)
from app.services.billing_ingestion.parsers.base import BaseBillingParser

REQUIRED_COLUMNS: Set[str] = {
    "billing_date",
    "cloud_provider",
    "account_id",
    "service_id",
    "service_name",
    "resource_id",
    "usage_type",
    "usage_quantity",
    "unit_of_measurement",
    "currency",
    "cost",
    "billing_amount",
    "workload_id",
    "product_feature_id",
}

PROVIDER_CANONICAL_MAP: Dict[str, str] = {
    "aws": "AWS",
    "amazon": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "microsoft": "Azure",
    "microsoft azure": "Azure",
}


class NormalizedBillingParser(BaseBillingParser):
    """Parses standard multi-cloud normalized billing CSV files."""

    @property
    def parser_name(self) -> str:
        return "normalized_csv"

    def can_parse(self, header_row: List[str]) -> bool:
        """Checks if the header contains all core normalized billing columns."""
        header_set = {col.strip().lower() for col in header_row if col}
        return REQUIRED_COLUMNS.issubset(header_set)

    def parse(self, stream: TextIO) -> IngestionReport:
        """Iterates over the CSV stream, validating each row independently."""
        report = IngestionReport()

        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            report.errors.append(
                RowValidationError(
                    row_number=1,
                    field="header",
                    error="Empty or missing CSV header row",
                )
            )
            return report

        # Normalize field names in the header
        field_map = {col.strip().lower(): col for col in reader.fieldnames if col}
        missing_required = REQUIRED_COLUMNS - set(field_map.keys())
        if missing_required:
            report.errors.append(
                RowValidationError(
                    row_number=1,
                    field="header",
                    error=f"CSV header is missing required columns: {sorted(list(missing_required))}",
                )
            )
            return report

        # Process data rows starting from line 2 (line 1 is header)
        for line_idx, raw_row in enumerate(reader, start=2):
            report.total_rows += 1

            # Check for empty line
            if not raw_row or not any(v.strip() for v in raw_row.values() if v):
                report.invalid_rows += 1
                report.errors.append(
                    RowValidationError(
                        row_number=line_idx,
                        field="row",
                        error="Row is completely empty or blank",
                        raw_data=raw_row,
                    )
                )
                continue

            # Validate row content
            parsed_record, error = self._validate_and_parse_row(raw_row, field_map, line_idx)
            if error:
                report.invalid_rows += 1
                report.errors.append(error)
            elif parsed_record:
                report.valid_rows += 1
                report.records.append(parsed_record)

                if parsed_record.billing_amount < 0:
                    report.total_credits += parsed_record.billing_amount
                else:
                    report.total_positive_charges += parsed_record.billing_amount

        # Compute net billing amount: positive charges + credits (where credits is negative)
        report.net_billing_amount = (report.total_positive_charges + report.total_credits).quantize(Decimal("0.0001"))
        report.total_positive_charges = report.total_positive_charges.quantize(Decimal("0.0001"))
        report.total_credits = report.total_credits.quantize(Decimal("0.0001"))

        return report

    def _validate_and_parse_row(
        self,
        raw_row: Dict[str, str],
        field_map: Dict[str, str],
        line_idx: int,
    ) -> tuple[Optional[ParsedBillingRecord], Optional[RowValidationError]]:
        """Validates individual column values for a single CSV data row."""

        def get_val(col_name: str) -> str:
            actual_col = field_map.get(col_name)
            return (raw_row.get(actual_col) or "").strip()

        # 1. Check Required Text Fields
        for req_field in [
            "account_id",
            "service_id",
            "service_name",
            "resource_id",
            "usage_type",
            "unit_of_measurement",
            "workload_id",
            "product_feature_id",
        ]:
            val = get_val(req_field)
            if not val:
                return None, RowValidationError(
                    row_number=line_idx,
                    field=req_field,
                    error=f"Required field '{req_field}' is missing or empty",
                    raw_data=raw_row,
                )

        # 2. Validate Billing Date
        date_str = get_val("billing_date")
        if not date_str:
            return None, RowValidationError(
                row_number=line_idx,
                field="billing_date",
                error="Required field 'billing_date' is missing",
                raw_data=raw_row,
            )
        try:
            parsed_date = date.fromisoformat(date_str)
        except ValueError:
            return None, RowValidationError(
                row_number=line_idx,
                field="billing_date",
                error=f"Invalid date format '{date_str}'. Expected ISO 8601 YYYY-MM-DD",
                raw_data=raw_row,
            )

        # 3. Validate Cloud Provider
        raw_provider = get_val("cloud_provider")
        canonical_provider = PROVIDER_CANONICAL_MAP.get(raw_provider.lower())
        if not canonical_provider:
            return None, RowValidationError(
                row_number=line_idx,
                field="cloud_provider",
                error=f"Unsupported cloud provider '{raw_provider}'. Supported: AWS, GCP, Azure",
                raw_data=raw_row,
            )

        # 4. Validate Currency
        curr_str = get_val("currency").upper()
        if len(curr_str) != 3 or not curr_str.isalpha():
            return None, RowValidationError(
                row_number=line_idx,
                field="currency",
                error=f"Invalid currency code '{curr_str}'. Expected 3-letter ISO currency code",
                raw_data=raw_row,
            )

        # 5. Validate Usage Quantity
        qty_str = get_val("usage_quantity")
        try:
            quantity = Decimal(qty_str)
        except (InvalidOperation, TypeError):
            return None, RowValidationError(
                row_number=line_idx,
                field="usage_quantity",
                error=f"Invalid numeric value for usage_quantity: '{qty_str}'",
                raw_data=raw_row,
            )

        # 6. Validate Financial Values (cost & billing_amount)
        cost_str = get_val("cost")
        try:
            cost = Decimal(cost_str)
        except (InvalidOperation, TypeError):
            return None, RowValidationError(
                row_number=line_idx,
                field="cost",
                error=f"Invalid numeric value for cost: '{cost_str}'",
                raw_data=raw_row,
            )

        billing_str = get_val("billing_amount")
        try:
            billing_amount = Decimal(billing_str)
        except (InvalidOperation, TypeError):
            return None, RowValidationError(
                row_number=line_idx,
                field="billing_amount",
                error=f"Invalid numeric value for billing_amount: '{billing_str}'",
                raw_data=raw_row,
            )

        # 7. Validate Resource Tags (optional, but if present must be valid JSON)
        actual_tags_col = field_map.get("resource_tags")
        tags_raw = (raw_row.get(actual_tags_col) or "").strip() if actual_tags_col else ""
        parsed_tags = {}
        if tags_raw:
            try:
                parsed_tags = json.loads(tags_raw)
                if not isinstance(parsed_tags, dict):
                    return None, RowValidationError(
                        row_number=line_idx,
                        field="resource_tags",
                        error="resource_tags must be a JSON object dictionary",
                        raw_data=raw_row,
                    )
            except Exception as exc:
                return None, RowValidationError(
                    row_number=line_idx,
                    field="resource_tags",
                    error=f"Malformed JSON in resource_tags: {str(exc)}",
                    raw_data=raw_row,
                )

        is_credit = billing_amount < 0

        record = ParsedBillingRecord(
            row_number=line_idx,
            billing_date=parsed_date,
            cloud_provider=canonical_provider,
            account_id=get_val("account_id"),
            service_id=get_val("service_id"),
            service_name=get_val("service_name"),
            resource_id=get_val("resource_id"),
            usage_type=get_val("usage_type"),
            usage_quantity=quantity,
            unit_of_measurement=get_val("unit_of_measurement"),
            currency=curr_str,
            cost=cost,
            billing_amount=billing_amount,
            workload_id=get_val("workload_id"),
            product_feature_id=get_val("product_feature_id"),
            resource_tags=parsed_tags,
            is_credit=is_credit,
        )

        return record, None
