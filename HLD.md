# MarginOps: High-Level Design (HLD)

---

## 1. System Architecture Overview

MarginOps is architected as an **enterprise modular monolith** with polyglot persistence, asynchronous background task processing, and a high-density single-page web application.

```mermaid
flowchart TD
    subgraph ClientTier ["Presentation Tier (React 19 + Tailwind CSS 4)"]
        UI_Dash["Executive Dashboard (KPIs)"]
        UI_Exp["Cost Explorer & Attribution Ledger"]
        UI_Econ["Unit Economics Scorecards"]
        UI_Anom["Anomaly Radar & Spend Forecast"]
        UI_War["AI Investigator War Room & Approval Gate"]
    end

    subgraph APITier ["Application Tier (FastAPI Modular Monolith)"]
        Router["API v1 Central Router Aggregator"]
        EP_Costs["/api/v1/costs"]
        EP_Econ["/api/v1/unit-economics"]
        EP_Anom["/api/v1/anomalies"]
        EP_Fore["/api/v1/forecasting"]
        EP_Inv["/api/v1/investigations"]
        EP_Health["/api/v1/health"]
    end

    subgraph EngineTier ["Domain Calculation & Intelligence Engines"]
        Eng_Attr["Deterministic Cost Attribution Engine (Hare-Niemeyer)"]
        Eng_Fusion["Unit Economics & Telemetry Fusion Engine"]
        Eng_Anom["Statistical Anomaly Detection Engine"]
        Eng_Fore["Holt's Linear Trend Forecasting Engine"]
        Eng_Agent["Evidence-Led AI Investigator Agent (Slide 06)"]
        Tools_Agent["Bounded Read-Only Investigation Tools"]
    end

    subgraph DataTier ["Polyglot Persistence Tier"]
        DB_Postgres[("PostgreSQL 16 (Relational Domain Ledger)")]
        DB_Mongo[("MongoDB 7.0 (Time-Series Telemetry)")]
        DB_Redis[("Redis 7.2 (Cache & Task Broker)")]
    end

    ClientTier -->|REST API / JSON| Router
    Router --> EP_Costs & EP_Econ & EP_Anom & EP_Fore & EP_Inv & EP_Health

    EP_Costs --> Eng_Attr
    EP_Econ --> Eng_Fusion
    EP_Anom --> Eng_Anom
    EP_Fore --> Eng_Fore
    EP_Inv --> Eng_Agent

    Eng_Agent --> Tools_Agent
    Tools_Agent --> DB_Postgres & DB_Mongo

    Eng_Attr --> DB_Postgres
    Eng_Fusion --> DB_Postgres & DB_Mongo
    Eng_Anom --> DB_Postgres
```

---

## 2. Technology Stack & Architectural Decision Records (ADRs)

| Component | Technology | Rationale & Architectural Trade-Off |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (Python 3.13)** | High-concurrency ASGI framework with native Pydantic v2 validation, automatic OpenAPI generation, and asynchronous I/O support. |
| **Architecture Pattern** | **Modular Monolith** | Avoids distributed microservice network overhead and eventual consistency issues; provides ACID transactions for ledger reconciliation while maintaining clean domain boundaries (`app/services/*`). |
| **Relational Storage** | **PostgreSQL 16** | ACID-compliant storage for financial records, multi-tenant lineage, allocation rules, and budgets. Enforces composite foreign keys `(organization_id, id)` for strict multi-tenancy. Accessed via SQLAlchemy 2.x asyncpg. |
| **Telemetry Storage** | **MongoDB 7.0** | Document store optimized for high-write, semi-structured telemetry logs and AI token metrics. Accessed via the **official PyMongo Async API** (`AsyncMongoClient`) with compound time-series indexes. |
| **Cache & Task Broker** | **Redis 7.2** | Sub-millisecond query caching, rate-limiting, and Celery asynchronous task broker. |
| **Frontend Framework** | **React 19 + TypeScript + Vite** | High-density enterprise SaaS interface built with strict static typing, client-side caching (TanStack Query v5), and component routing. |
| **CSS Framework** | **Tailwind CSS 4** | High-density styling via `@tailwindcss/vite` without PostCSS pipeline overhead, enforcing a sleek Linear/Datadog dark theme design system. |

---

## 3. Data Flow & Ingestion Pipeline Architecture

```mermaid
sequenceDiagram
    autonumber
    actor Cloud as Multi-Cloud Billing Export
    participant Ingest as Billing Ingestion Service
    participant Hash as SHA-256 Idempotency Filter
    participant Ledger as PostgreSQL Cost Ledger
    participant Attr as Cost Attribution Engine
    participant Agent as AI Investigator

    Cloud->>Ingest: Ingest Billing CSV (AWS, GCP, Azure)
    Ingest->>Hash: Compute Batch SHA-256 Checksum
    alt Duplicate Checksum Exists
        Hash-->>Ingest: Reject Duplicate Batch (HTTP 409 Conflict)
    else New Valid Batch
        Hash->>Ledger: Persist ImportBatch & CostRecords (ACID Transaction)
        Ledger-->>Ingest: Batch Committed
        Ingest->>Attr: Execute Deterministic Attribution
        Attr->>Attr: Hare-Niemeyer Largest Remainder Calculation
        Attr-->>Ledger: Persist Attributed Items (Δ = $0.0000)
        opt Spend Outlier Flagged
            Attr->>Agent: Trigger Anomaly Investigation
            Agent->>Agent: 5-Step Diagnostic Protocol
        end
    end
```

### 3.1. Ingestion Normalization
The ingestion pipeline processes multi-cloud line items from AWS Cost & Usage Reports (CUR), GCP Cloud Billing, and Azure Cost Management into a single canonical data structure (`ParsedBillingRecord`):
- Canonical provider normalization: `"Amazon Web Services"` $\rightarrow$ `"AWS"`, `"Google Cloud"` $\rightarrow$ `"GCP"`, `"Microsoft Azure"` $\rightarrow$ `"Azure"`.
- Monetary values stored strictly as exact 4-decimal `Decimal` instances (`Numeric(18, 4)`).
- Symmetrical handling of credits, rebates, and SLA discounts as negative billing amounts.

---

## 4. Deterministic Cost Attribution Engine Architecture

### 4.1. The Mathematical Invariant
To satisfy strict accounting standards, the attribution engine guarantees the **Conservation of Money**:
$$\sum_{r \in \text{Records}} \text{SourceAmount}(r) = \sum_{a \in \text{Allocated}} \text{Amount}(a) + \sum_{u \in \text{Unallocated}} \text{Amount}(u)$$
$$\Delta = \text{Total Source} - (\text{Total Allocated} + \text{Total Unallocated}) = \$0.0000$$

### 4.2. Hare-Niemeyer (Largest Remainder) Penny Distribution
When shared infrastructure costs (e.g. Kubernetes cluster nodes or staging databases) are divided between multiple features or cost centers, fractional cents cannot be rounded independently without creating cash leakage.
MarginOps implements the **Hare-Niemeyer method**:
1. Compute exact theoretical shares: $s_i = \frac{A \cdot w_i}{\sum w}$.
2. Floor all shares to precision quantum: $b_i = \lfloor s_i \rfloor$.
3. Compute the unrounded remainder: $R = A - \sum b_i$.
4. Sort targets by remainder fraction $r_i = s_i - b_i$ in descending order.
5. Distribute one quantum ($0.0001$) to the largest remainders until $R = 0$.
6. Symmetrically supports negative credits and refunds without sign inversion errors.

### 4.3. Multi-Tier Waterfall Pipeline
```mermaid
flowchart TD
    Record["Normalized Cost Record"] --> C1{"Direct Product Feature ID Present?"}
    C1 -- Yes --> A1["Direct Feature Attribution (Priority 0)"]
    C1 -- No --> C2{"Workload ID Mapped to Feature?"}
    C2 -- Yes --> A2["Direct Workload Attribution (Priority 1)"]
    C2 -- No --> C3{"Matches TAG_EXACT Rule?"}
    C3 -- Yes --> A3["Rule Allocation (Tag Exact)"]
    C3 -- No --> C4{"Matches TAG_PREFIX Rule?"}
    C4 -- Yes --> A4["Rule Allocation (Tag Prefix)"]
    C4 -- No --> C5{"Matches FIXED_PERCENTAGE Rule?"}
    C5 -- Yes --> A5["Hare-Niemeyer Proportional Split"]
    C5 -- No --> U1["Preserved as UNALLOCATED Item (Audit Trail)"]
```

---

## 5. Unit Economics & Telemetry Fusion Engine Architecture

The Unit Economics Engine fuses financial infrastructure COGS (from PostgreSQL) with operational telemetry streams (from MongoDB):

```mermaid
flowchart LR
    subgraph FinanceLedger ["PostgreSQL Financial COGS"]
        Cost_Search["Semantic Search: $2,150.00"]
        Cost_Copilot["AI Copilot RAG: $5,800.00"]
        Cost_Det["Anomaly Detector: $2,950.00"]
    end

    subgraph TelemetryStream ["MongoDB PyMongo Async Telemetry"]
        Tel_Search["240,000 API Requests"]
        Tel_Copilot["18,000,000 Inference Tokens"]
        Tel_Det["100,000 Background Jobs"]
    end

    subgraph FusionEngine ["Unit Economics Fusion Engine"]
        F1["$/kReq = ($2,150 / 240k) * 1,000 = $8.96/kReq"]
        F2["$/MTok = ($5,800 / 18M) * 1M = $322.22/MTok"]
        F3["Scorecard: Margin = (Rev - COGS) / Rev"]
    end

    FinanceLedger --> FusionEngine
    TelemetryStream --> FusionEngine
    FusionEngine --> Scorecard["Gross Margin Compliance Matrix (HEALTHY vs CRITICAL)"]
```

---

## 6. Spend Forecasting Engine Architecture (Holt's Linear Trend)

The forecasting engine utilizes **Holt's Double Exponential Smoothing** on historical daily spend series:
1. **Level Equation**:
   $$\ell_t = \alpha Y_t + (1 - \alpha)(\ell_{t-1} + b_{t-1})$$
2. **Trend Equation**:
   $$b_t = \beta (\ell_t - \ell_{t-1}) + (1 - \beta)b_{t-1}$$
3. **Forecast Horizon ($h$ days ahead)**:
   $$\hat{Y}_{t+h} = \ell_t + h b_t$$
4. **Confidence Bounds (80% and 95%)**:
   $$\text{Lower / Upper Bound} = \hat{Y}_{t+h} \pm z \cdot \hat{\sigma} \sqrt{1 + (h-1)\alpha^2}$$

---

## 7. Evidence-Led AI Investigator & Governed Gate Architecture (Slide 06)

```mermaid
stateDiagram-v2
    [*] --> Triggered: Statistical Anomaly Detected
    Triggered --> GatheringEvidence: Investigator Agent Invoked
    
    state GatheringEvidence {
        [*] --> QueryCostLedger: Read-Only Tool
        QueryCostLedger --> QueryTelemetry: Read-Only Tool
        QueryTelemetry --> InspectMetadata: Read-Only Tool
    }

    GatheringEvidence --> Analyzing: Evidence Package Assembled
    
    state Analyzing {
        [*] --> RankHypotheses: Calibrate Confidence (0.0 to 1.0)
        RankHypotheses --> FormulateOptions: Savings & Risk Assessment
    }

    Analyzing --> PendingApproval: Action Card Generated with SHA-256 Audit Seal
    
    state PendingApproval {
        [*] --> ReviewerDecision
        ReviewerDecision --> Approved: Human Reviewer Signature
        ReviewerDecision --> Rejected: Human Reviewer Rejection
        ReviewerDecision --> Dismissed: False Positive Dismissal
    }

    Approved --> [*]: Audit Log Committed
    Rejected --> [*]: Audit Log Committed
    Dismissed --> [*]: Audit Log Committed
```

### Safety Invariants:
1. **Bounded Read-Only Tools**: The AI Agent only possesses query tools (`query_cost_ledger`, `query_telemetry`, `inspect_metadata`).
2. **Zero Direct Mutation**: The Agent cannot terminate instances, update configurations, or modify cloud provider resources.
3. **Cryptographic SHA-256 Audit Hash**: Every action card contains an immutable audit hash sealing the evidence and decision.

---

## 8. Deployment & Infrastructure Topology

The platform deploys via `docker-compose.yml` orchestrating isolated containers on an internal network (`marginops-network`):

| Container | Image | Ports | Role |
| :--- | :--- | :--- | :--- |
| `marginops-postgres` | `postgres:16-alpine` | `5432:5432` | Relational domain database with health check |
| `marginops-mongo` | `mongo:7.0` | `27017:27017` | Telemetry document database |
| `marginops-redis` | `redis:7.2-alpine` | `6379:6379` | Cache & Celery broker |
| `marginops-backend` | Python 3.13 ASGI | `8000:8000` | FastAPI modular monolith |
| `marginops-frontend`| React 19 + Vite | `5173:5173` | Production web application |
