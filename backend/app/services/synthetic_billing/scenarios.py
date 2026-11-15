"""Ground-truth scenario definitions and simulation logic for MarginOps."""
from datetime import date, timedelta
from decimal import Decimal
import json
from typing import Dict, List, Tuple
from app.services.synthetic_billing.models import BillingRecord, ScenarioGroundTruth


class ScenarioManager:
    """Manages injection of realistic FinOps scenarios and compiles ground-truth manifest."""

    def __init__(self, start_date: date, total_days: int):
        self.start_date = start_date
        self.total_days = total_days
        self.end_date = start_date + timedelta(days=total_days - 1)

    def get_date_for_day(self, day_index: int) -> str:
        """Helper returning ISO date string for 1-based day index."""
        current_date = self.start_date + timedelta(days=day_index - 1)
        return current_date.isoformat()

    def generate_scenario_records(self, rng) -> Tuple[List[BillingRecord], List[ScenarioGroundTruth]]:
        """Generates billing records for all 5 scenarios and returns the ground-truth metadata."""
        records: List[BillingRecord] = []
        ground_truth: List[ScenarioGroundTruth] = []

        # ----------------------------------------------------------------------
        # Scenario 1: Unexpected Compute Cost Spike (Days 42-46)
        # ----------------------------------------------------------------------
        sc1_start_day, sc1_end_day = 42, 46
        sc1_start_str = self.get_date_for_day(sc1_start_day)
        sc1_end_str = self.get_date_for_day(sc1_end_day)
        sc1_rate = Decimal("1.3600")  # c6i.8xlarge
        sc1_total_cost = Decimal("0.0000")

        for d in range(sc1_start_day, sc1_end_day + 1):
            d_str = self.get_date_for_day(d)
            # 14 to 18 runaway nodes running 24 hours
            nodes = rng.randint(14, 18)
            hours = Decimal(str(nodes * 24))
            cost = (hours * sc1_rate).quantize(Decimal("0.0001"))
            sc1_total_cost += cost

            records.append(
                BillingRecord(
                    billing_date=d_str,
                    cloud_provider="AWS",
                    account_id="aws-org-123456789012",
                    service_id="AmazonEC2",
                    service_name="Amazon Elastic Compute Cloud",
                    resource_id="i-worker-pipeline-runaway",
                    usage_type="BoxUsage:c6i.8xlarge",
                    usage_quantity=hours,
                    unit_of_measurement="Hours",
                    currency="USD",
                    cost=cost,
                    billing_amount=cost,
                    workload_id="workload-data-pipeline",
                    product_feature_id="feat-anomaly-detector",
                    resource_tags=json.dumps({"Environment": "production", "Component": "etl-worker-pool", "Team": "data-infra"}),
                )
            )

        ground_truth.append(
            ScenarioGroundTruth(
                scenario_id="SCENARIO-COMPUTE-SPIKE-001",
                scenario_type="compute_spike",
                title="Runaway ETL Worker Cluster Auto-scaling Spike",
                description="A poison-pill message loop in the ingestion queue triggered runaway horizontal scaling of 14-18 c6i.8xlarge EC2 worker nodes for 5 days until manual intervention.",
                cloud_provider="AWS",
                target_service="AmazonEC2",
                target_resource_id="i-worker-pipeline-runaway",
                target_workload_id="workload-data-pipeline",
                target_product_feature_id="feat-anomaly-detector",
                start_date=sc1_start_str,
                end_date=sc1_end_str,
                expected_cost_impact=sc1_total_cost.quantize(Decimal("0.01")),
                detection_criteria={"metric": "daily_cost", "z_score_threshold": 3.5, "percentage_increase": 800},
                metadata={"affected_nodes_peak": 18, "instance_type": "c6i.8xlarge"},
            )
        )

        # ----------------------------------------------------------------------
        # Scenario 2: Gradual Storage Cost Increase (Days 20-120)
        # ----------------------------------------------------------------------
        sc2_start_day = 20
        sc2_end_day = self.total_days
        sc2_start_str = self.get_date_for_day(sc2_start_day)
        sc2_end_str = self.get_date_for_day(sc2_end_day)
        sc2_rate = Decimal("0.000767")  # $0.023 / 30 days
        sc2_total_cost = Decimal("0.0000")
        current_gb = Decimal("100.0000")

        for d in range(sc2_start_day, sc2_end_day + 1):
            d_str = self.get_date_for_day(d)
            # Accumulates +50 to +65 GB each day
            daily_growth = Decimal(str(rng.randint(50, 65)))
            current_gb += daily_growth
            cost = (current_gb * sc2_rate).quantize(Decimal("0.0001"))
            sc2_total_cost += cost

            records.append(
                BillingRecord(
                    billing_date=d_str,
                    cloud_provider="AWS",
                    account_id="aws-org-123456789012",
                    service_id="AmazonS3",
                    service_name="Amazon Simple Storage Service",
                    resource_id="arn:aws:s3:::marginops-prod-raw-telemetry",
                    usage_type="TimedStorage-ByteHrs",
                    usage_quantity=current_gb,
                    unit_of_measurement="GB-Mo",
                    currency="USD",
                    cost=cost,
                    billing_amount=cost,
                    workload_id="workload-storage-lake",
                    product_feature_id="feat-cost-intelligence",
                    resource_tags=json.dumps({"Environment": "production", "Bucket": "telemetry-raw", "Team": "core-platform"}),
                )
            )

        ground_truth.append(
            ScenarioGroundTruth(
                scenario_id="SCENARIO-STORAGE-LEAK-002",
                scenario_type="storage_leak",
                title="Accumulating Raw Telemetry S3 Bucket Without Lifecycle Expiration",
                description="Uncompressed raw JSON telemetry logs accumulated continuously without lifecycle rules transitioning objects to Glacier or expiring them, scaling storage from 100 GB to over 6,000 GB.",
                cloud_provider="AWS",
                target_service="AmazonS3",
                target_resource_id="arn:aws:s3:::marginops-prod-raw-telemetry",
                target_workload_id="workload-storage-lake",
                target_product_feature_id="feat-cost-intelligence",
                start_date=sc2_start_str,
                end_date=sc2_end_str,
                expected_cost_impact=sc2_total_cost.quantize(Decimal("0.01")),
                detection_criteria={"metric": "daily_storage_growth", "trend": "monotonically_increasing", "days_continuous": 30},
                metadata={"initial_gb": 100, "final_gb": float(current_gb)},
            )
        )

        # ----------------------------------------------------------------------
        # Scenario 3: AI/LLM Usage Cost Surge (Days 75-88)
        # ----------------------------------------------------------------------
        sc3_start_day, sc3_end_day = 75, 88
        sc3_start_str = self.get_date_for_day(sc3_start_day)
        sc3_end_str = self.get_date_for_day(sc3_end_day)
        sc3_rate = Decimal("0.0150")  # $0.0150 per kToken
        sc3_total_cost = Decimal("0.0000")

        for d in range(sc3_start_day, sc3_end_day + 1):
            d_str = self.get_date_for_day(d)
            # Surges from ~450 kTokens to 12,000-16,000 kTokens/day
            surge_ktokens = Decimal(str(rng.randint(12000, 16000)))
            cost = (surge_ktokens * sc3_rate).quantize(Decimal("0.0001"))
            sc3_total_cost += cost

            records.append(
                BillingRecord(
                    billing_date=d_str,
                    cloud_provider="AWS",
                    account_id="aws-org-123456789012",
                    service_id="AmazonBedrock",
                    service_name="Amazon Bedrock",
                    resource_id="anthropic.claude-3-5-sonnet-surge",
                    usage_type="TokenUsage:Output",
                    usage_quantity=surge_ktokens,
                    unit_of_measurement="kTokens",
                    currency="USD",
                    cost=cost,
                    billing_amount=cost,
                    workload_id="workload-model-inference",
                    product_feature_id="feat-ai-copilot",
                    resource_tags=json.dumps({"Environment": "production", "Model": "claude-3-5-sonnet", "Team": "ai-infra"}),
                )
            )

        ground_truth.append(
            ScenarioGroundTruth(
                scenario_id="SCENARIO-AI-SURGE-003",
                scenario_type="ai_token_surge",
                title="Generative AI Copilot Recursive Reflection Loop Surge",
                description="Deployment of multi-agent reflective reasoning caused unbounded token consumption loops, creating an 18x surge in daily output tokens for a 14-day period.",
                cloud_provider="AWS",
                target_service="AmazonBedrock",
                target_resource_id="anthropic.claude-3-5-sonnet-surge",
                target_workload_id="workload-model-inference",
                target_product_feature_id="feat-ai-copilot",
                start_date=sc3_start_str,
                end_date=sc3_end_str,
                expected_cost_impact=sc3_total_cost.quantize(Decimal("0.01")),
                detection_criteria={"metric": "token_output_volume", "multiplier": 15.0, "affected_service": "AmazonBedrock"},
                metadata={"average_surge_ktokens": 14000},
            )
        )

        # ----------------------------------------------------------------------
        # Scenario 4: Unused or Underutilized Resources (Days 1-120)
        # ----------------------------------------------------------------------
        sc4_start_day = 1
        sc4_end_day = self.total_days
        sc4_start_str = self.get_date_for_day(sc4_start_day)
        sc4_end_str = self.get_date_for_day(sc4_end_day)
        sc4_rate = Decimal("0.5200")  # db.r6g.xlarge ($12.48/day)
        sc4_total_cost = Decimal("0.0000")

        for d in range(sc4_start_day, sc4_end_day + 1):
            d_str = self.get_date_for_day(d)
            hours = Decimal("24.0000")
            cost = (hours * sc4_rate).quantize(Decimal("0.0001"))
            sc4_total_cost += cost

            records.append(
                BillingRecord(
                    billing_date=d_str,
                    cloud_provider="AWS",
                    account_id="aws-org-123456789012",
                    service_id="AmazonRDS",
                    service_name="Amazon Relational Database Service",
                    resource_id="db-marginops-staging-replica-orphaned",
                    usage_type="InstanceUsage:db.r6g.xlarge",
                    usage_quantity=hours,
                    unit_of_measurement="Hours",
                    currency="USD",
                    cost=cost,
                    billing_amount=cost,
                    workload_id="workload-database-cluster",
                    product_feature_id="feat-infra-optimizer",
                    resource_tags=json.dumps({"Environment": "staging", "Component": "read-replica", "Team": "db-infra"}),
                )
            )

        ground_truth.append(
            ScenarioGroundTruth(
                scenario_id="SCENARIO-IDLE-ZOMBIE-004",
                scenario_type="underutilized_resource",
                title="Orphaned Staging RDS Read Replica Running Continuously",
                description="An unutilized staging read replica provisioned for testing remained running 24/7 across the entire 120-day timeframe with zero active connections, generating continuous idle waste.",
                cloud_provider="AWS",
                target_service="AmazonRDS",
                target_resource_id="db-marginops-staging-replica-orphaned",
                target_workload_id="workload-database-cluster",
                target_product_feature_id="feat-infra-optimizer",
                start_date=sc4_start_str,
                end_date=sc4_end_str,
                expected_cost_impact=sc4_total_cost.quantize(Decimal("0.01")),
                detection_criteria={"metric": "cpu_utilization_avg", "threshold_pct": 1.0, "active_connections": 0, "status": "idle"},
                metadata={"idle_days": self.total_days, "daily_waste": 12.48},
            )
        )

        # ----------------------------------------------------------------------
        # Scenario 5: Billing Credits and Refunds (Days 25, 65, 105)
        # ----------------------------------------------------------------------
        credits = [
            (
                25,
                "AWS",
                "aws-org-123456789012",
                "AWSBilling",
                "AWS Account Billing",
                "credit-aws-startup-grant",
                "Credit:PromotionalDiscount",
                Decimal("1.0000"),
                "Adjustment",
                Decimal("-2500.0000"),
                "workload-finance",
                "feat-cost-intelligence",
                {"Type": "promotional-credit", "Program": "AWS-Activate-Startup"},
            ),
            (
                65,
                "AWS",
                "aws-org-123456789012",
                "AWSBilling",
                "AWS Account Billing",
                "refund-aws-sla-credit-outage",
                "Refund:ServiceLevelAgreement",
                Decimal("1.0000"),
                "Adjustment",
                Decimal("-450.0000"),
                "workload-finance",
                "feat-cost-intelligence",
                {"Type": "sla-credit", "Incident": "INC-AWS-USEAST1-OUTAGE"},
            ),
            (
                105,
                "Azure",
                "sub-marginops-azure-ai",
                "AzureBilling",
                "Microsoft Azure Billing",
                "rebate-azure-ea-commitment",
                "Credit:CommitmentRebate",
                Decimal("1.0000"),
                "Adjustment",
                Decimal("-1250.0000"),
                "workload-finance",
                "feat-cost-intelligence",
                {"Type": "commitment-discount", "Agreement": "EA-ANNUAL-COMMIT"},
            ),
        ]

        sc5_total_credit = Decimal("0.0000")
        for day_idx, prov, acct, s_id, s_name, res_id, u_type, qty, unit, amt, wl_id, feat_id, tags in credits:
            d_str = self.get_date_for_day(day_idx)
            sc5_total_credit += amt
            records.append(
                BillingRecord(
                    billing_date=d_str,
                    cloud_provider=prov,
                    account_id=acct,
                    service_id=s_id,
                    service_name=s_name,
                    resource_id=res_id,
                    usage_type=u_type,
                    usage_quantity=qty,
                    unit_of_measurement=unit,
                    currency="USD",
                    cost=amt,
                    billing_amount=amt,
                    workload_id=wl_id,
                    product_feature_id=feat_id,
                    resource_tags=json.dumps(tags),
                )
            )

        ground_truth.append(
            ScenarioGroundTruth(
                scenario_id="SCENARIO-CREDITS-REFUNDS-005",
                scenario_type="credit_refund",
                title="Cloud Provider Enterprise Credits and SLA Outage Refunds",
                description="Valid financial adjustments on the billing ledger: $2,500 AWS startup grant (Day 25), $450 AWS SLA downtime refund (Day 65), and $1,250 Azure Enterprise rebate (Day 105).",
                cloud_provider="Multi-Cloud",
                target_service="CloudBilling",
                target_resource_id="credit-aws-startup-grant,refund-aws-sla-credit-outage,rebate-azure-ea-commitment",
                target_workload_id="workload-finance",
                target_product_feature_id="feat-cost-intelligence",
                start_date=self.get_date_for_day(25),
                end_date=self.get_date_for_day(105),
                expected_cost_impact=sc5_total_credit.quantize(Decimal("0.01")),
                detection_criteria={"field": "billing_amount", "condition": "negative", "expected_total": -4200.00},
                metadata={"credit_count": 3, "total_refund_amount": float(sc5_total_credit)},
            )
        )

        return records, ground_truth
