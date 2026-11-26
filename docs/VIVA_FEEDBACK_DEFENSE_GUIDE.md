# MarginOps — Viva Examination Defense Guide (Rubric & Code Citations)

> **Based on Official Viva Feedback (November 2026)**  
> **Objective**: Transition from generic conceptual answers to high-authority, senior-engineer answers citing **exact file paths, class names, functions, and line numbers** in the MarginOps codebase.

---

## Question 1: Async Data Fetching & Error Handling (Executive Dashboard)

### The Examiner's Question
> *"When fetching data for the Executive Dashboard, how does the application handle potential API request failures or timeouts to ensure a robust user experience, as suggested by the need for loading and error states in asynchronous data fetching?"*

### Why the Previous Answer Needed Improvement
* The previous answer gave a generic definition of loading/error states without naming libraries, timeouts, or project files.

### The Senior Engineer Answer (What to Say)
> *"In MarginOps, asynchronous data fetching is handled through a coordinated two-tier architecture: **Axios** on the network transport layer and **TanStack React Query (v5)** on the UI state layer.*
>
> 1. * **Network Timeout & Client Configuration** (`frontend/src/services/api.ts`, lines 15–21):*
>    *We configure a centralized `apiClient` using Axios with a strict `timeout: 10000` (10 seconds) and base URL pointing to `/api/v1`. If the backend is unreachable or latency exceeds 10 seconds, Axios automatically aborts the request and throws an `ECONNABORTED` timeout error instead of letting the UI hang indefinitely.*
>
> 2. * **Component Query Lifecycle** (`frontend/src/pages/DashboardPage.tsx`, lines 24–41):*
>    *The Executive Dashboard imports `useQuery` from `@tanstack/react-query` to fetch `/costs/summary`, `/health`, and `/spend/forecast`. TanStack Query exposes reactive boolean states: `isLoading`, `isError`, `error`, and `data`.*
>
> 3. * **Resilience & Graceful Degradation** (`frontend/src/pages/DashboardPage.tsx`):*
>    *While `kpiLoading` is true, the dashboard displays skeleton placeholders and pulse animations to prevent layout shifts. If an API request fails, TanStack Query executes an exponential backoff retry (3 attempts) before transitioning to `isError`. If the failure persists, the dashboard renders an inline error alert card with a 'Retry' action instead of crashing the React component tree.*
>
> 4. * **Background Polling** (`frontend/src/pages/DashboardPage.tsx`, lines 27, 33, 39):*
>    *We configure `refetchInterval: 15000` (15s) for KPI metrics and `refetchInterval: 30000` (30s) for spend forecasts, ensuring live telemetry without full page refreshes.*"

---

## Question 2: Client-Side Routing & TanStack Query (`DashboardPage.tsx`)

### The Examiner's Question
> *"The `DashboardPage.tsx` component imports `useQuery` from `@tanstack/react-query`. How does this hook, and potentially its configuration like `refetchInterval`, contribute to the client-side routing experience by managing data fetching and UI updates within its designated route?"*

### Why the Previous Answer Needed Improvement
* The previous answer explained `useQuery` in isolation but did not connect it to **client-side routing mechanisms** (navigation, route caching, stale-while-revalidate).

### The Senior Engineer Answer (What to Say)
> *"In a client-side routed Single Page Application (using React Router v6 in `frontend/src/App.tsx`), navigating between routes (`/`, `/costs`, `/unit-economics`, `/anomalies`, `/investigator`) unmounts and mounts view components without reloading the browser document.*
>
> *Here is how `useQuery` in `DashboardPage.tsx` optimizes the routing experience:*
>
> 1. * **Query Cache & Stale-While-Revalidate Across Route Transitions**:*
>    *`useQuery` ties data to a unique cache key (`queryKey: ['kpi-summary']`). When a user navigates away from `/` to `/costs` and later clicks back to the Dashboard, TanStack Query immediately serves the cached data from memory in $0\text{ms}$. The user experiences instantaneous client-side navigation with zero blank screens or layout shifts.*
>
> 2. * **Non-Blocking Background Revalidation (`refetchInterval: 15000`)**:*
>    *While the route is actively mounted, `refetchInterval` silently polls the backend every 15 seconds. If fresh data has arrived, the UI updates reactively. Crucially, when the user navigates to another route, TanStack Query automatically unsubscribes the polling interval, conserving client CPU cycles and network bandwidth.*
>
> 3. * **Decoupling Data Fetching from Router Lifecycle**:*
>    *Instead of relying on blocking route loaders that stall client-side navigation until network requests complete, `useQuery` allows the route component to transition immediately while asynchronously managing fetch lifecycles in the background.*"

---

## Question 3: Problem Modeling — Hare-Niemeyer Algorithm Implementation

### The Examiner's Question & Practice Prompt
> *"Can you show me where in the MarginOps codebase the Hare-Niemeyer algorithm is implemented and how the proportional shares and remainders are calculated to ensure zero penny leakage?"*

### Why the Previous Answer Needed Improvement
* The previous answer described the mathematical concept of Largest Remainder but did not cite any code, functions, or implementation files.

### The Senior Engineer Answer (What to Say)
> *"The Hare-Niemeyer Largest Remainder method is implemented in **`backend/app/services/cost_attribution/engine.py`**, specifically inside the pure calculation function **`distribute_amount_by_weights()`** (lines 28–80).*
>
> *Here is the exact algorithmic implementation:*
>
> 1. * **Arbitrary Decimal Precision** (`engine.py`, lines 28–36):*
>    *The function takes `amount: Decimal`, `weights: Sequence[Decimal]`, and `precision: Decimal = Decimal("0.0001")`. We strictly avoid Python floating-point `float` to eliminate binary floating-point rounding errors.*
>
> 2. * **Calculating Base Integer Shares** (`engine.py`, lines 54–58):*
>    ```python
>    exact_shares = [(abs_amount * w) / total_weight for w in weights]
>    base_shares = [s.quantize(precision, rounding=ROUND_FLOOR) for s in exact_shares]
>    ```
>    *We compute the unrounded theoretical share for each feature, then floor each share to the precision quantum (`0.0001` sub-cents).*
>
> 3. * **Computing the Discrepancy & Fractional Remainders** (`engine.py`, lines 59–70):*
>    ```python
>    remainder_to_distribute = abs_amount - sum(base_shares)
>    quanta_to_distribute = int((remainder_to_distribute / precision).to_integral_exact(rounding=ROUND_HALF_UP))
>    fractional_remainders = [(exact_shares[i] - base_shares[i], i) for i in range(len(weights))]
>    fractional_remainders.sort(key=lambda item: (item[0], -item[1]), reverse=True)
>    ```
>    *We calculate the exact remainder and sort all features in descending order by the magnitude of their fractional remainder. We use the original index `i` as a stable tie-breaker for deterministic reproducibility.*
>
> 4. * **Distributing Remaining Quanta** (`engine.py`, lines 72–79):*
>    ```python
>    final_shares = list(base_shares)
>    for k in range(quanta_to_distribute):
>        idx = fractional_remainders[k % len(fractional_remainders)][1]
>        final_shares[idx] += precision
>    ```
>    *We distribute the remaining sub-cents one-by-one to the features with the largest fractions. If the transaction is a credit or refund (`amount < 0`), the signs are preserved symmetrically.*
>
> *This guarantees: $\sum \text{final\_shares} \equiv \text{amount}$ down to $\$0.0000$, verified by 24 unit tests in `backend/tests/test_cost_attribution.py`.*"

---

## Question 4: System Design & Concurrency (asyncpg + PyMongo Async)

### The Examiner's Question
> *"The HLD specifies using SQLAlchemy 2.x with asyncpg for PostgreSQL and the official PyMongo Async API for MongoDB. How does this choice impact the application's concurrency and performance when handling requests that involve both data stores?"*

### Why the Previous Answer Needed Improvement
* The previous answer explained asynchronous I/O conceptually, but did not mention how simultaneous requests are orchestrated across both databases with code examples.

### The Senior Engineer Answer (What to Say)
> *"MarginOps uses a **Polyglot Persistence architecture**: PostgreSQL 16 stores ACID-relational financial ledgers, organizations, and budgets, while MongoDB 7.0 stores high-throughput, semi-structured telemetry events and LLM token usage.*
>
> 1. * **Database Driver Configurations**:*
>    * **PostgreSQL** (`backend/app/core/database.py`, lines 9–24): Built with SQLAlchemy 2.x's `create_async_engine()` powered by **`asyncpg`**, the fastest binary PostgreSQL driver for Python. It uses `async_sessionmaker(class_=AsyncSession, expire_on_commit=False)`.*
>    * **MongoDB** (`backend/app/core/mongo.py`, lines 14–30): Configured with the official **`AsyncMongoClient`** from PyMongo, avoiding legacy blocking drivers.*
>
> 2. * **Handling Concurrent Requests Across Both Stores** (`backend/app/services/unit_economics/engine.py`):*
>    *In endpoints like `/api/v1/unit-economics/report`, the backend must retrieve product features and allocation budgets from PostgreSQL while simultaneously aggregating millions of telemetry records from MongoDB.*
>    *Because both drivers are non-blocking, we use Python's **`asyncio.gather()`** to execute the PostgreSQL query and MongoDB aggregation pipeline concurrently in the same asyncio event loop:*
>    ```python
>    # Pseudo-code pattern in unit economics aggregation
>    features_task = session.execute(select(ProductFeature).where(...))
>    telemetry_task = mongo_db[TELEMETRY_COLLECTION].aggregate(pipeline).to_list(length=None)
>    features_result, telemetry_result = await asyncio.gather(features_task, telemetry_task)
>    ```
>
> 3. * **Impact on Concurrency & Performance**:*
>    *In a traditional synchronous architecture, querying Postgres then Mongo sequentially blocks the worker thread for the sum of both latencies ($T_{\text{PG}} + T_{\text{Mongo}}$). With `asyncpg` and `AsyncMongoClient`, execution is interleaved: total latency is $\max(T_{\text{PG}}, T_{\text{Mongo}})$, and worker threads yield control during I/O wait, allowing a single Uvicorn process to handle thousands of concurrent client connections.*"

---

## Question 5: RESTful Endpoint Design & Routing Architecture

### The Examiner's Question & Practice Prompt
> *"Can you show me an example of a specific endpoint path in your `backend/app/api/v1/endpoints/...` file for managing cost data, and explain why that particular path and HTTP method were chosen?"*

### Why the Previous Answer Needed Improvement
* The previous answer gave general definitions of GET/POST/PUT/DELETE without citing actual MarginOps routes, parameters, or design rationales.

### The Senior Engineer Answer (What to Say)
> *"In MarginOps, all cost intelligence endpoints are defined in **`backend/app/api/v1/endpoints/costs.py`** and mounted under `/api/v1/costs` by `backend/app/api/v1/router.py`.*
>
> *Here are three concrete examples of our REST design choices:*
>
> 1. * **`GET /api/v1/costs/explorer`** (`costs.py`, lines 17–59):*
>    * **Why GET?**: Cost exploration is an **idempotent, safe retrieval operation** with zero side effects on the database.*
>    * **URL Design & Query Parameters**: Filtering and pagination criteria are passed as query parameters: `provider=AWS`, `service=Amazon Bedrock`, `workload=inference`, `page=1`, `limit=50`. This follows RESTful standards by keeping the URI noun-based (`/costs/explorer`) while parameterizing the representation.*
>    * **Response Contract**: Returns a structured payload containing paginated line items alongside an aggregated `daily_time_series` array for frontend charts.*
>
> 2. * **`POST /api/v1/costs/upload`** (`costs.py`, lines 72–99):*
>    * **Why POST?**: Uploading a multi-cloud billing CSV is a **non-idempotent state mutation**. It ingests new line items, validates content against FOCUS 1.0 schemas, calculates SHA-256 batch checksums, and dynamically triggers the Hare-Niemeyer attribution engine.*
>    * **Design Choice**: Consumes `multipart/form-data` with `file: UploadFile`. If an identical batch checksum is uploaded twice, it rejects the submission with `409 Conflict`.*
>
> 3. * **`GET /api/v1/costs/export`** (`costs.py`, lines 101–119):*
>    * **Why GET?**: Generating a financial audit certificate is a read operation parameterized by format (`?format=csv` or `?format=json`). When CSV is requested, it returns a streaming `Response` with headers `Content-Disposition: attachment; filename=...` and `media_type="text/csv"`.*"

---

## Question 6: Error Handling & Frontend Initialization (`frontend/src/main.tsx`)

### The Examiner's Question
> *"In `frontend/src/main.tsx`, a check `if (!rootElement)` throws an error if the root element is not found. How does this specific error handling contribute to the overall robustness of the frontend application during initialization?"*

### Why the Previous Answer Needed Improvement
* Could elaborate on potential real-world failure scenarios where the root element might be missing, and the technical implications of throwing vs not throwing.

### The Senior Engineer Answer (What to Say)
> *"In `frontend/src/main.tsx`, lines 6–9:*
> ```typescript
> const rootElement = document.getElementById('root');
> if (!rootElement) {
>   throw new Error('Failed to find root element');
> }
> ReactDOM.createRoot(rootElement).render(...);
> ```
>
> *This guard check establishes enterprise-grade robustness in three ways:*
>
> 1. * **TypeScript Type Narrowing & Null Safety**:*
>    *`document.getElementById()` has a return type of `HTMLElement | null`. Without this explicit check, TypeScript would require an unsafe non-null assertion (`rootElement!`). If `rootElement` were null at runtime, calling `ReactDOM.createRoot(rootElement)` would trigger an obscure runtime error deep inside React internals: `TypeError: Cannot read properties of null (reading 'render')`, which provides zero diagnostic context in production error logs.*
>
> 2. * **Real-World Scenarios Where `rootElement` is Missing**:*
>    * **HTML Template Corruption**: A broken CI/CD build or CDN caching error that serves a misconfigured `index.html` where `<div id="root">` was renamed or removed.*
>    * **Third-Party Script Injection**: Browser extensions, ad-blockers, or enterprise proxy scripts altering or stripping the DOM tree prior to script execution.*
>    * **Micro-Frontend / Embedding Embeds**: If MarginOps is embedded inside an enterprise host dashboard as a Web Component or iframe, script race conditions can cause bundle execution before the host DOM container is mounted.*
>
> 3. * **Fail-Fast Architectural Principle**:*
>    *By throwing `throw new Error('Failed to find root element')` immediately during bootstrap, the application halts predictably at the entry boundary. This triggers top-level error monitoring hooks (like Datadog RUM or Sentry) with an actionable, high-priority alert instead of degrading silently into a blank white screen.*"

---

## Question 7: Schema Modeling & Multi-Tenancy (`allocation_rule.py`)

### The Examiner's Question
> *"The `backend/app/models/allocation_rule.py` file defines a schema. Can you explain the purpose of the `organization_id` field and how it enforces multi-tenancy within the allocation rules data?"*

### The Senior Engineer Answer (What to Say)
> *"In `backend/app/models/allocation_rule.py`, `organization_id` is the foundational multi-tenant partition key across both storage and business logic.*
>
> 1. * **Tenant Foreign Key & Indexing** (`allocation_rule.py`, lines 55–60):*
>    *`organization_id: Mapped[uuid.UUID]` is a non-nullable foreign key referencing `organizations.id` with `ondelete="CASCADE"`. It is indexed (`index=True`) to guarantee $O(\log N)$ tenant-scoped lookup performance during high-throughput attribution runs.*
>
> 2. * **Composite Foreign Key Constraints (Zero Cross-Tenant Contamination)** (`allocation_rule.py`, lines 40–52):*
>    *Crucially, MarginOps enforces multi-tenancy not just in application code, but directly at the PostgreSQL database schema level using **composite foreign keys**:*
>    ```python
>    ForeignKeyConstraint(
>        ["organization_id", "product_feature_id"],
>        ["product_features.organization_id", "product_features.id"],
>        ondelete="CASCADE",
>        name="fk_allocation_rule_product_feature_same_org",
>    )
>    ```
>    *This database constraint mathematically guarantees that an allocation rule belonging to Organization A can **never** reference a product feature belonging to Organization B. Even if an application-layer bug occurred, the database itself rejects the insert with a foreign key violation.*
>
> 3. * **Query Partitioning in Calculation Engines** (`backend/app/services/cost_attribution/engine.py`):*
>    *When cost attribution executes, rules and features are filtered strictly by `organization_id`. Verified by 7 automated tests in `backend/tests/test_tenant_integrity.py`, cross-tenant references are rejected with `TenantIsolationViolationError`.*"
