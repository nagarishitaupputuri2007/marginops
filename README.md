# MarginOps — Autonomous FinOps & Product Economics Platform

[![Tests](https://img.shields.io/badge/tests-134%20passed-brightgreen.svg)](#test-suite--quality-gate)
[![Architecture](https://img.shields.io/badge/architecture-Microservices%20%7C%20Polyglot%20Ledger-blue.svg)](#system-architecture)
[![Reconciliation](https://img.shields.io/badge/reconciliation-%CE%94%20%3D%20%240.0000%20(100%25)-success.svg)](#1-deterministic-cost-attribution-engine-hare-niemeyer)
[![Anomaly Detection](https://img.shields.io/badge/recall-100%25%20(5%2F5%20Ground%20Truth)-teal.svg)](#3-statistical-anomaly-detection--holts-spend-forecasting)
[![License](https://img.shields.io/badge/license-Apache--2.0-lightgrey.svg)](LICENSE)

> **MarginOps** is an enterprise-grade multi-cloud infrastructure cost intelligence, FinOps attribution, and real-time product economics platform. It transforms fragmented, multi-cloud billing line items (AWS, GCP, Azure) and distributed application telemetry into an audit-sealed unit economics ledger, statistical anomaly detections with Holt's linear trend forecasts, and governed AI-led incident remediation.

---

## Executive Summary & Value Proposition

Traditional cloud cost dashboards (e.g. AWS Cost Explorer, Datadog Cloud Cost Management) report aggregate infrastructure spend, leaving engineering and finance leaders with three critical blind spots:

1. **The Shared-Cost Attribution Problem**: Multi-tenant clusters (Kubernetes worker pools, shared RDS databases, central vector stores) cannot be cleanly allocated to customer contracts or product features, resulting in accounting drift and floating-point penny leakage.
2. **The Unit Economics Disconnect**: Finance sees raw dollar spend; engineering sees request counts and token volume. MarginOps mathematically fuses distributed telemetry with billing data to compute real-time **Cost per 1k Requests** and **Cost per 1M LLM Tokens** against recognized revenue.
3. **Reactive Alert Fatigue & Destructive AI Risks**: Traditional threshold alerts fire hours after budget overruns occur. MarginOps deploys dual-window statistical anomaly detection (Modified Z-Score + Holt's forecasting) paired with a **Bounded Read-Only AI Investigator** whose remediation proposals require cryptographic human approval.

---

## System Architecture

```
                           +--------------------------------------------------------+
                           |           MarginOps High-Density React 19 UI           |
                           |   (Vite, TypeScript, Tailwind CSS 4, Lucide Icons)     |
                           +---------------------------+----------------------------+
                                                       | REST API / JSON
                                                       v
+---------------------------------------------------------------------------------------------------+
|                                MarginOps Core FastAPI Backend                                     |
|                                                                                                   |
|  +-------------------------+  +--------------------------+  +----------------------------------+  |
|  | Multi-Cloud Ingestion   |  | Hare-Niemeyer Ledger     |  | Unit Economics & Margins         |  |
|  | - AWS CUR 2.0 / FOCUS   |  | - Largest Remainder      |  | - Cost per 1k Requests           |  |
|  | - GCP BigQuery Export   |  | - Absolute Conservation  |  | - Cost per 1M Tokens             |  |
|  | - Azure Cost Management |  | - Zero Penny Leakage     |  | - Gross Margin Health Matrix     |  |
|  +-------------------------+  +--------------------------+  +----------------------------------+  |
|                                                                                                   |
|  +-------------------------------------+  +----------------------------------------------------+  |
|  | Statistical Radar & Holt Forecast   |  | Governed AI Investigator Agent                     |  |
|  | - Modified Z-Score Dual-Window     |  | - Read-Only Forensic Tool Harness                  |  |
|  | - Holt's Double Exponential Trend   |  | - Automated 5-Step Diagnostic Loop                 |  |
|  | - 80% & 95% Analytical Intervals    |  | - SHA-256 Governed Human Approval Gate             |  |
|  +-------------------------------------+  +----------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
                                                       |
                                                       v
+---------------------------------------------------------------------------------------------------+
|                                  Polyglot Persistence Layer                                       |
|  +------------------------------+  +------------------------------+  +-------------------------+  |
|  | PostgreSQL 16                |  | MongoDB 7.0                  |  | Redis 7.2               |  |
|  | Relational Ledger, Tenants,  |  | Raw Normalized Billing Items |  | In-Memory Cache, Metric |  |
|  | Invoices & Audit Log (ACID)  |  | & Polymorphic Telemetry      |  | Aggregates & Rate Limits|  |
|  +------------------------------+  +------------------------------+  +-------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## Core Engineering & Mathematical Innovations

### 1. Deterministic Cost Attribution Engine (Hare-Niemeyer)
Standard proportional cost allocation using floating-point division produces rounding errors where $\sum \text{allocated}_i \ne \text{source\_cost}$. 

MarginOps implements the **Hare-Niemeyer (Largest Remainder) algorithm** over arbitrary precision `Decimal` numbers:
1. Computes exact integer base allocations: $\lfloor w_i \times S \rfloor$ (in sub-cents, 4 decimal places).
2. Computes remainders: $r_i = (w_i \times S) - \lfloor w_i \times S \rfloor$.
3. Sorts fractions descending and distributes the remaining discrepancy one sub-cent at a time:
$$\Delta = \text{Source Spend} - \sum_{i=1}^{N} \text{Allocated}_i \equiv \$0.0000$$

### 2. Unit Economics & Telemetry Fusion Engine
MarginOps normalizes disparate telemetry streams (REST API ingress counts, Vector DB query loads, LLM prompt/completion token consumption) and fuses them with daily allocated infrastructure costs:
* **Cost per 1,000 API Requests ($/kReq)**: Direct compute and ingress cost attributed per feature workload.
* **Cost per 1M LLM Tokens ($/MTok)**: Blended model inference spend across Bedrock, Azure OpenAI, and Anthropic.
* **Feature Gross Margin Categorization**: Real-time evaluation into health tiers:
  - `HEALTHY` ($\ge 65\%$)
  - `WARNING` ($40\% - 64\%$)
  - `CRITICAL` ($0\% - 39\%$)
  - `NEGATIVE` ($< 0\%$, feature losing money)
  - `NO_REVENUE` (Internal platform overhead)

### 3. Statistical Anomaly Detection & Holt's Spend Forecasting
* **Dual-Window Robust Z-Score**: Evaluates short-term spend deviations (7-day window) against baseline variance (30-day window) using the Median Absolute Deviation (MAD), resilient to historical outliers:
$$M_i = \frac{0.6745 \times (x_i - \tilde{x})}{\text{MAD}}$$
* **Holt's Linear Exponential Smoothing**: Generates multi-day spend trajectories incorporating both baseline level ($L_t$) and trend trajectory ($T_t$):
$$L_t = \alpha Y_t + (1 - \alpha)(L_{t-1} + T_{t-1})$$
$$T_t = \beta (L_t - L_{t-1}) + (1 - \beta) T_{t-1}$$
$$\hat{Y}_{t+h} = L_t + h T_t \pm z \cdot \hat{\sigma}_e \sqrt{h}$$
* Evaluated against a rigorous 5-scenario ground-truth benchmark suite with **100% precision and recall**.

### 4. Evidence-Led AI Investigator with Cryptographic Human Approval
* **Bounded Read-Only Tools**: The AI Agent is equipped strictly with inspection tools (`query_cost_ledger`, `fetch_telemetry_metrics`, `correlate_deployment_events`, `calculate_unit_margin_impact`). It possesses zero write permissions to cloud infrastructure.
* **Cryptographic Human Approval Gate**: When an anomaly requires mitigation, the agent generates an actionable Terraform/CLI remediation plan. Execution requires an authenticated human engineer signature, verified via an immutable SHA-256 payload digest.

---

## Repository Structure

```
marginops/
├── PRD.md                       # Certified Product Requirements Document
├── HLD.md                       # Certified High-Level Architecture Design
├── LLD.md                       # Certified Low-Level Technical Specification
├── README.md                    # Platform Overview & Engineering Documentation
├── docker-compose.yml           # Full-stack multi-container orchestration
├── backend/
│   ├── Dockerfile               # Multi-stage Python 3.13 production image
│   ├── pyproject.toml           # Poetry / Pip dependencies & test config
│   ├── app/
│   │   ├── main.py              # FastAPI application factory & CORS
│   │   ├── api/v1/endpoints/    # REST routes (costs, unit_economics, anomalies, etc.)
│   │   ├── core/                # System settings, security, logging
│   │   ├── models/              # Polyglot schemas (SQLAlchemy, Pydantic, Mongo)
│   │   └── services/            # Pure calculation & attribution engines
│   └── tests/                   # 134 automated unit, integration, and benchmark tests
├── frontend/
│   ├── Dockerfile               # Multi-stage Node 22 build + Nginx alpine
│   ├── nginx.conf               # SPA routing & reverse proxy configuration
│   ├── package.json             # React 19, TypeScript, Tailwind CSS 4
│   └── src/
│       ├── App.tsx              # Root router & notification toast provider
│       ├── components/          # Reusable UI cards, tables, charts
│       ├── pages/               # 5 Primary Views (Dashboard, CostExplorer, etc.)
│       └── services/api.ts      # Typed client with live backend endpoints
├── docs/                        # Architecture specs and Viva examination scripts
└── scripts/                     # Turnkey launch and validation automation
```

---

## Quickstart & Local Setup

### Prerequisites
* **Docker & Docker Compose** (for turnkey containerized execution) OR
* **Python 3.13+** and **Node.js 20+** (for bare-metal development)

### Option A: Turnkey Docker Deployment (Recommended)

To launch the full 5-container production stack (PostgreSQL, MongoDB, Redis, FastAPI Backend, React Frontend):

```bash
# Clone the repository
git clone https://github.com/nagarishitaupputuri2007/marginops.git
cd marginops

# Start all services with health checks
docker compose up -d --build

# Verify running containers
docker compose ps
```

* **Frontend Web Application**: [http://localhost:3000](http://localhost:3000)
* **Backend REST API**: [http://localhost:8000](http://localhost:8000)
* **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Bare-Metal Local Development

#### 1. Backend Service
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -e .

# Run all 134 tests
pytest -v

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Application
```bash
cd frontend
npm install
npm run build   # Verify TypeScript and Vite production bundle
npm run dev     # Starts development server at http://localhost:5173
```

---

## Test Suite & Quality Gate

MarginOps maintains a strict zero-regression quality standard. All financial algorithms and API contracts are validated by an automated test harness:

```bash
======================= 134 passed in 2.67s ========================
```

| Test Category | Suite File | Test Count | Assertion Focus |
|---|---|---|---|
| **Attribution Engine** | `test_cost_attribution.py` | 24 | Hare-Niemeyer remainder, zero-leakage conservation |
| **Unit Economics** | `test_unit_economics.py` | 12 | $/kReq, $/MTok, gross margin health classification |
| **Anomaly Detection** | `test_anomaly_detection.py` | 6 | 100% recall on 5 ground-truth injection scenarios |
| **Spend Forecasting** | `test_forecasting.py` | 3 | Holt's linear smoothing, 80% & 95% analytical bands |
| **AI Investigator** | `test_investigator.py` | 10 | Bounded tools, forensic citations, SHA-256 seal |
| **API Endpoints** | `test_api_endpoints.py` | 11 | REST contracts, CSV upload, financial audit export |
| **Telemetry & Ingestion**| `test_telemetry_schemas.py` | 22 | FOCUS 1.0 schema, synthetic billing generator |
| **Tenant Integrity** | `test_tenant_integrity.py` | 7 | Cross-tenant data isolation & partition boundaries |

---

## Key REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System readiness and connected storage status |
| `GET` | `/api/v1/costs/summary` | Top-line spend ($13,095.41), provider splits, and ledger delta ($\Delta = \$0.0000$) |
| `GET` | `/api/v1/costs/explorer` | Multi-cloud line item table with provider/service filtering |
| `POST`| `/api/v1/costs/upload` | Ingest external multi-cloud billing CSV with instant reconciliation |
| `GET` | `/api/v1/costs/export` | Download compliance-ready financial audit CSV |
| `GET` | `/api/v1/unit-economics/metrics`| Feature-level unit economics ($/kReq, $/MTok, gross margins) |
| `GET` | `/api/v1/anomalies/active` | Active detected anomalies with forensic root causes |
| `GET` | `/api/v1/anomalies/forecast`| Holt's 14-day spend forecast with confidence intervals |
| `POST`| `/api/v1/investigations/trigger`| Run autonomous 5-step AI investigation |
| `POST`| `/api/v1/investigations/{id}/approve` | Cryptographically seal and approve remediation plan |

---

## Specification Documents & Viva Resources

* **[Product Requirements Document (PRD)](file:///c:/Users/urish/OneDrive/Desktop/MarginOps/marginops/PRD.md)**: Product goals, functional requirements, non-functional constraints, and user journeys.
* **[High-Level Design (HLD)](file:///c:/Users/urish/OneDrive/Desktop/MarginOps/marginops/HLD.md)**: System architecture, component diagrams, polyglot data layer, and failure domains.
* **[Low-Level Design (LLD)](file:///c:/Users/urish/OneDrive/Desktop/MarginOps/marginops/LLD.md)**: Data schemas, algorithmic proofs, state machines, and mathematical equations.
* **[Viva & Demo Runbook Guide](file:///c:/Users/urish/OneDrive/Desktop/MarginOps/marginops/docs/VIVA_AND_DEMO_SCRIPT.md)**: 5-minute presentation script with click paths, exact numbers, and examiner FAQ defense.

---

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
