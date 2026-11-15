"""Cloud provider catalog and resource templates for synthetic billing data."""
from decimal import Decimal
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class ResourceTemplate(BaseModel):
    """Specification template for a simulated cloud infrastructure resource."""
    cloud_provider: str
    account_id: str
    service_id: str
    service_name: str
    resource_id: str
    usage_type: str
    unit_of_measurement: str
    unit_rate: Decimal = Field(..., description="Cost per unit in USD")
    base_daily_quantity: Decimal = Field(..., description="Typical daily usage quantity")
    quantity_noise_pct: float = Field(default=0.05, description="Daily random fluctuation (e.g., 0.05 = +/- 5%)")
    workload_id: str
    product_feature_id: str
    default_tags: Dict[str, str] = Field(default_factory=dict)
    weekday_multiplier: float = Field(default=1.05, description="Traffic multiplier on weekdays (Mon-Fri)")
    weekend_multiplier: float = Field(default=0.75, description="Traffic multiplier on weekends (Sat-Sun)")


def get_default_resource_templates() -> List[ResourceTemplate]:
    """Returns baseline cloud resource catalog spanning AWS, GCP, and Azure."""
    return [
        # --- AWS Resources ---
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            resource_id="i-0a81f349c2d1e001",
            usage_type="BoxUsage:m6i.xlarge",
            unit_of_measurement="Hours",
            unit_rate=Decimal("0.1920"),
            base_daily_quantity=Decimal("24.0000"),
            quantity_noise_pct=0.0,
            workload_id="workload-api-gateway",
            product_feature_id="feat-cost-intelligence",
            default_tags={"Environment": "production", "Component": "api-gateway", "Team": "core-platform"},
            weekday_multiplier=1.0,
            weekend_multiplier=1.0,
        ),
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            resource_id="i-0a81f349c2d1e002",
            usage_type="BoxUsage:m6i.xlarge",
            unit_of_measurement="Hours",
            unit_rate=Decimal("0.1920"),
            base_daily_quantity=Decimal("24.0000"),
            quantity_noise_pct=0.0,
            workload_id="workload-api-gateway",
            product_feature_id="feat-cost-intelligence",
            default_tags={"Environment": "production", "Component": "api-gateway-replica", "Team": "core-platform"},
            weekday_multiplier=1.0,
            weekend_multiplier=1.0,
        ),
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            resource_id="i-worker-pipeline-01",
            usage_type="BoxUsage:c6i.4xlarge",
            unit_of_measurement="Hours",
            unit_rate=Decimal("0.6800"),
            base_daily_quantity=Decimal("24.0000"),
            quantity_noise_pct=0.08,
            workload_id="workload-data-pipeline",
            product_feature_id="feat-anomaly-detector",
            default_tags={"Environment": "production", "Component": "etl-worker", "Team": "data-infra"},
            weekday_multiplier=1.10,
            weekend_multiplier=0.70,
        ),
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonRDS",
            service_name="Amazon Relational Database Service",
            resource_id="db-marginops-primary",
            usage_type="InstanceUsage:db.r6g.xlarge",
            unit_of_measurement="Hours",
            unit_rate=Decimal("0.5200"),
            base_daily_quantity=Decimal("24.0000"),
            quantity_noise_pct=0.0,
            workload_id="workload-database-cluster",
            product_feature_id="feat-cost-intelligence",
            default_tags={"Environment": "production", "Component": "primary-oltp", "Team": "db-infra"},
            weekday_multiplier=1.0,
            weekend_multiplier=1.0,
        ),
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonRDS",
            service_name="Amazon Relational Database Service",
            resource_id="db-marginops-primary-storage",
            usage_type="StorageUsage:GP3",
            unit_of_measurement="GB-Mo",
            unit_rate=Decimal("0.003833"),  # $0.115 / 30 days
            base_daily_quantity=Decimal("600.0000"),
            quantity_noise_pct=0.01,
            workload_id="workload-database-cluster",
            product_feature_id="feat-cost-intelligence",
            default_tags={"Environment": "production", "Component": "db-storage", "Team": "db-infra"},
            weekday_multiplier=1.0,
            weekend_multiplier=1.0,
        ),
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonBedrock",
            service_name="Amazon Bedrock",
            resource_id="anthropic.claude-3-5-sonnet-input",
            usage_type="TokenUsage:Input",
            unit_of_measurement="kTokens",
            unit_rate=Decimal("0.0030"),  # $3.00 / 1M tokens = $0.003 / 1k tokens
            base_daily_quantity=Decimal("1800.0000"),  # 1.8M input tokens/day
            quantity_noise_pct=0.15,
            workload_id="workload-model-inference",
            product_feature_id="feat-ai-copilot",
            default_tags={"Environment": "production", "Model": "claude-3-5-sonnet", "Team": "ai-infra"},
            weekday_multiplier=1.20,
            weekend_multiplier=0.60,
        ),
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonBedrock",
            service_name="Amazon Bedrock",
            resource_id="anthropic.claude-3-5-sonnet-output",
            usage_type="TokenUsage:Output",
            unit_of_measurement="kTokens",
            unit_rate=Decimal("0.0150"),  # $15.00 / 1M tokens = $0.015 / 1k tokens
            base_daily_quantity=Decimal("450.0000"),  # 450k output tokens/day
            quantity_noise_pct=0.18,
            workload_id="workload-model-inference",
            product_feature_id="feat-ai-copilot",
            default_tags={"Environment": "production", "Model": "claude-3-5-sonnet", "Team": "ai-infra"},
            weekday_multiplier=1.20,
            weekend_multiplier=0.60,
        ),
        ResourceTemplate(
            cloud_provider="AWS",
            account_id="aws-org-123456789012",
            service_id="AmazonCloudWatch",
            service_name="Amazon CloudWatch",
            resource_id="cw-marginops-metrics",
            usage_type="MetricStorage:Standard",
            unit_of_measurement="GB-Mo",
            unit_rate=Decimal("0.0100"),  # $0.30 / 30 days
            base_daily_quantity=Decimal("85.0000"),
            quantity_noise_pct=0.05,
            workload_id="workload-monitoring",
            product_feature_id="feat-infra-optimizer",
            default_tags={"Environment": "production", "Component": "observability", "Team": "sre"},
            weekday_multiplier=1.05,
            weekend_multiplier=0.90,
        ),

        # --- GCP Resources ---
        ResourceTemplate(
            cloud_provider="GCP",
            account_id="gcp-proj-marginops-prod",
            service_id="GoogleComputeEngine",
            service_name="Google Compute Engine",
            resource_id="gke-analytics-worker-01",
            usage_type="N2-Standard-8:Core",
            unit_of_measurement="Hours",
            unit_rate=Decimal("0.3884"),
            base_daily_quantity=Decimal("24.0000"),
            quantity_noise_pct=0.02,
            workload_id="workload-data-pipeline",
            product_feature_id="feat-unit-metrics",
            default_tags={"Environment": "production", "Cluster": "gke-analytics", "Team": "analytics"},
            weekday_multiplier=1.10,
            weekend_multiplier=0.75,
        ),
        ResourceTemplate(
            cloud_provider="GCP",
            account_id="gcp-proj-marginops-prod",
            service_id="BigQuery",
            service_name="Google BigQuery",
            resource_id="bq-cost-intelligence-warehouse",
            usage_type="AnalysisUsage:OnDemand",
            unit_of_measurement="TB",
            unit_rate=Decimal("6.2500"),  # $6.25 per TB scanned
            base_daily_quantity=Decimal("1.8000"),  # 1.8 TB/day
            quantity_noise_pct=0.20,
            workload_id="workload-data-pipeline",
            product_feature_id="feat-cost-intelligence",
            default_tags={"Environment": "production", "Dataset": "cost_dw", "Team": "bi-team"},
            weekday_multiplier=1.30,
            weekend_multiplier=0.40,
        ),
        ResourceTemplate(
            cloud_provider="GCP",
            account_id="gcp-proj-marginops-prod",
            service_id="CloudStorage",
            service_name="Google Cloud Storage",
            resource_id="gcs-marginops-cold-backups",
            usage_type="StorageUsage:Coldline",
            unit_of_measurement="GB-Mo",
            unit_rate=Decimal("0.000133"),  # $0.004 / 30 days
            base_daily_quantity=Decimal("1200.0000"),
            quantity_noise_pct=0.01,
            workload_id="workload-storage-lake",
            product_feature_id="feat-cost-intelligence",
            default_tags={"Environment": "production", "Bucket": "cold-backups", "Team": "secops"},
            weekday_multiplier=1.0,
            weekend_multiplier=1.0,
        ),

        # --- Azure Resources ---
        ResourceTemplate(
            cloud_provider="Azure",
            account_id="sub-marginops-azure-ai",
            service_id="AzureOpenAI",
            service_name="Azure OpenAI Service",
            resource_id="deployment-gpt-4o-shared",
            usage_type="TokenUsage:Inference",
            unit_of_measurement="kTokens",
            unit_rate=Decimal("0.0050"),  # $5.00 / 1M tokens
            base_daily_quantity=Decimal("1200.0000"),  # 1.2M tokens/day
            quantity_noise_pct=0.15,
            workload_id="workload-model-inference",
            product_feature_id="feat-ai-copilot",
            default_tags={"Environment": "production", "Model": "gpt-4o", "Team": "ai-infra"},
            weekday_multiplier=1.25,
            weekend_multiplier=0.55,
        ),
        ResourceTemplate(
            cloud_provider="Azure",
            account_id="sub-marginops-azure-ai",
            service_id="AzureCosmosDB",
            service_name="Azure Cosmos DB",
            resource_id="cosmos-infra-graph-db",
            usage_type="ProvisionedThroughput:RU",
            unit_of_measurement="100-RU/s-Hours",
            unit_rate=Decimal("0.0080"),
            base_daily_quantity=Decimal("240.0000"),  # 10 * 24 hours
            quantity_noise_pct=0.0,
            workload_id="workload-database-cluster",
            product_feature_id="feat-infra-optimizer",
            default_tags={"Environment": "production", "Database": "infra-graph", "Team": "platform-eng"},
            weekday_multiplier=1.0,
            weekend_multiplier=1.0,
        ),
    ]
