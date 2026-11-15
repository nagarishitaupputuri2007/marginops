"""Synthetic Cloud Billing Data Generation CLI Script for MarginOps.

Generates a realistic 120-day multi-cloud billing benchmark dataset (CSV)
alongside an isolated ground-truth manifest (JSON) for evaluation.
"""
import argparse
from datetime import date
from decimal import Decimal
import logging
from pathlib import Path
import sys

# Ensure backend directory is in python search path
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.synthetic_billing import (  # noqa: E402
    GenerationConfig,
    SyntheticBillingGenerator,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("marginops.billing_generator")


def main():
    parser = argparse.ArgumentParser(
        description="Generate MarginOps 120-day multi-cloud synthetic billing dataset and ground-truth manifest."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=120,
        help="Number of days to simulate (default: 120)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic reproducibility (default: 42)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2026-07-18",
        help="Timeline start date in YYYY-MM-DD format (default: 2026-07-18)",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=str(repo_root / "data" / "synthetic" / "cloud_billing_120d.csv"),
        help="Path for output billing CSV file",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=str(repo_root / "data" / "evaluation" / "ground_truth_anomalies.json"),
        help="Path for output ground-truth anomalies JSON manifest",
    )

    args = parser.parse_args()

    start_date_obj = date.fromisoformat(args.start_date)
    config = GenerationConfig(
        start_date=start_date_obj,
        days=args.days,
        seed=args.seed,
    )

    logger.info("Initializing MarginOps Synthetic Billing Generator...")
    logger.info(f"Timeline: {config.days} days ({config.start_date} to {config.start_date + date.resolution * (config.days - 1)})")
    logger.info(f"Deterministic seed: {config.seed}")

    generator = SyntheticBillingGenerator(config=config)
    manifest = generator.generate_and_save(
        output_csv=args.output_csv,
        output_json=args.output_json,
    )

    logger.info("Generation completed successfully!")
    logger.info(f"CSV Billing Dataset:  {args.output_csv} ({manifest.total_records:,} line items)")
    logger.info(f"Ground-Truth Manifest: {args.output_json} ({len(manifest.scenarios)} scenarios)")
    logger.info(f"Gross Cloud Spend:    ${manifest.total_gross_cost:,.2f}")
    logger.info(f"Total Credits/Refunds: ${manifest.total_credits:,.2f}")
    logger.info(f"Net Cloud Spend:      ${manifest.total_net_cost:,.2f}")
    logger.info("Injected Scenarios:")
    for sc in manifest.scenarios:
        logger.info(f"  - [{sc.scenario_id}] {sc.title} (${sc.expected_cost_impact:,.2f} impact)")


if __name__ == "__main__":
    main()
