"""Synthetic Cloud Billing Generator engine for MarginOps."""
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import random
from typing import List, Tuple

from app.services.synthetic_billing.models import (
    BillingRecord,
    DatasetManifest,
    GenerationConfig,
    ScenarioGroundTruth,
)
from app.services.synthetic_billing.providers import (
    ResourceTemplate,
    get_default_resource_templates,
)
from app.services.synthetic_billing.scenarios import ScenarioManager


class SyntheticBillingGenerator:
    """Deterministic, high-fidelity synthetic cloud billing data generator."""

    def __init__(self, config: GenerationConfig = None):
        self.config = config or GenerationConfig()
        self.rng = random.Random(self.config.seed)
        self.templates = get_default_resource_templates()
        self.scenario_manager = ScenarioManager(
            start_date=self.config.start_date,
            total_days=self.config.days,
        )

    def generate(self) -> Tuple[List[BillingRecord], DatasetManifest]:
        """Runs the deterministic simulation and returns the billing records and manifest."""
        all_records: List[BillingRecord] = []

        # 1. Generate Baseline Records across all 120 days
        for day_idx in range(1, self.config.days + 1):
            current_date = self.config.start_date + timedelta(days=day_idx - 1)
            date_str = current_date.isoformat()
            is_weekend = current_date.weekday() >= 5  # Saturday=5, Sunday=6

            for template in self.templates:
                multiplier = template.weekend_multiplier if is_weekend else template.weekday_multiplier
                noise_range = template.quantity_noise_pct
                noise_factor = 1.0 + (self.rng.uniform(-noise_range, noise_range) if noise_range > 0 else 0.0)

                adjusted_qty = (template.base_daily_quantity * Decimal(str(multiplier)) * Decimal(str(noise_factor))).quantize(Decimal("0.0001"))
                cost = (adjusted_qty * template.unit_rate).quantize(Decimal("0.0001"))

                record = BillingRecord(
                    billing_date=date_str,
                    cloud_provider=template.cloud_provider,
                    account_id=template.account_id,
                    service_id=template.service_id,
                    service_name=template.service_name,
                    resource_id=template.resource_id,
                    usage_type=template.usage_type,
                    usage_quantity=adjusted_qty,
                    unit_of_measurement=template.unit_of_measurement,
                    currency=self.config.currency,
                    cost=cost,
                    billing_amount=cost,
                    workload_id=template.workload_id,
                    product_feature_id=template.product_feature_id,
                    resource_tags=json.dumps(template.default_tags),
                )
                all_records.append(record)

        # 2. Inject Scenario & Ground-Truth Records
        scenario_records, ground_truth_scenarios = self.scenario_manager.generate_scenario_records(self.rng)
        all_records.extend(scenario_records)

        # 3. Sort Chronologically by (billing_date, cloud_provider, service_id, resource_id)
        all_records.sort(key=lambda r: (r.billing_date, r.cloud_provider, r.service_id, r.resource_id))

        # 4. Compute Financial Aggregates
        total_gross = sum(r.cost for r in all_records if r.cost > 0)
        total_credits = sum(r.cost for r in all_records if r.cost < 0)
        total_net = total_gross + total_credits

        providers = sorted(list(set(r.cloud_provider for r in all_records)))
        services = sorted(list(set(r.service_name for r in all_records)))
        workloads = sorted(list(set(r.workload_id for r in all_records)))
        features = sorted(list(set(r.product_feature_id for r in all_records)))

        end_date = self.config.start_date + timedelta(days=self.config.days - 1)

        manifest = DatasetManifest(
            dataset_name="MarginOps 120-Day Multi-Cloud Synthetic Billing Benchmark",
            version="1.0.0",
            generated_at=datetime.now(timezone.utc).isoformat(),
            seed=self.config.seed,
            days_covered=self.config.days,
            start_date=self.config.start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_records=len(all_records),
            total_gross_cost=total_gross.quantize(Decimal("0.01")),
            total_credits=total_credits.quantize(Decimal("0.01")),
            total_net_cost=total_net.quantize(Decimal("0.01")),
            currency=self.config.currency,
            providers=providers,
            services=services,
            workloads=workloads,
            features=features,
            scenarios=ground_truth_scenarios,
        )

        return all_records, manifest

    def write_csv(self, output_path: str, records: List[BillingRecord]) -> None:
        """Writes billing records to a standard CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(BillingRecord.csv_header())
            for record in records:
                writer.writerow(record.to_csv_row())

    def write_manifest(self, output_path: str, manifest: DatasetManifest) -> None:
        """Writes dataset manifest and ground-truth scenarios to a JSON file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

    def generate_and_save(self, output_csv: str, output_json: str) -> DatasetManifest:
        """Runs generation and writes both CSV dataset and JSON manifest to disk."""
        records, manifest = self.generate()
        self.write_csv(output_csv, records)
        self.write_manifest(output_json, manifest)
        return manifest
