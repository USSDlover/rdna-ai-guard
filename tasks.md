# 🗺️ RDNA AI GUARD // MASTER PROJECT ROADMAP

This master blueprint tracks the remaining production phases of **RDNA AI Guard**. Tasks are structurally decoupled across the **Frontend (Feature-Driven Design)**, **Backend (FastAPI/Scapy)**, and **AI/Infrastructure** layers to eliminate development overlaps.

---

## 🧭 PHASE 1: FRONTEND REFINEMENT & CORE IMPLEMENTATION
*Focus: Scaling the Angular 19+ Signal architectures and finalizing layout views.*

### 🟩 Task FE-101: Complete the Cyber-Grid Telemetry Table
* **Target Directory:** `frontend/src/app/features/cyber-grid/`
* **Objective:** Expand the initial mock component into a robust, scrollable monitoring station.
* **Requirements:**
    * Implement full pagination or virtual scrolling for the event array.
    * Use Tailwind to design explicit threat status indicator badges (`PASSED` / `ESCALATED`).
    * Bind interactive detail modal triggers—clicking a row must expand a pane showing the full JSON configuration packet.
* **Dependencies:** None (Uses existing `CyberStateService` streaming loops).

### 🟩 Task FE-102: Build the Financial Ledger Audit Feature
* **Target Directory:** `frontend/src/app/features/ledger-audit/`
* **Objective:** Create the second primary product viewport tracking cross-border cash routing and syndicate fraud.
* **Requirements:**
    * Scaffold `features/ledger-audit/components/ledger-dashboard/`.
    * Scaffold `features/ledger-audit/data-access/ledger-state.service.ts`.
    * Set up an internal computed Signal filter that extracts *only* incoming logs where `primary_vector === 'FRAUD'`.
    * Build a UI graph component (using Chart.js, Ngx-Charts, or plain SVG bars) tracking transaction amounts and velocity metrics over time.
* **Dependencies:** Update `app.routes.ts` to attach this feature to the `/dashboard/ledger-audit` routing branch.

### 🟩 Task FE-103: Implement Global State Notifications
* **Target Directory:** `frontend/src/app/shared/` or `frontend/src/app/core/`
* **Objective:** Create an overlay notification banner system that surfaces sudden high-severity threat vectors immediately, regardless of which screen the operator is on.
* **Requirements:**
    * Build a centralized alert notification banner component.
    * Inject `TelemetryStreamService` into this banner.
    * Trigger a sliding toast alert every time a log arrives with a `risk_score > 85`.

---

## ⚙️ PHASE 2: REAL-TIME BACKEND ARCHITECTURE
*Focus: Moving from high-fidelity mock loops to actual infrastructure bindings.*

### 🟨 Task BE-201: Setup PostgreSQL Async Database Sync
* **Target Directory:** `backend/app/models/` and `backend/app/core/`
* **Objective:** Configure persistence storage tracking for every incoming packet payload.
* **Requirements:**
    * Define actual relational table entities using SQLModel/SQLAlchemy.
    * Build database connection initializers using an asynchronous driver configuration (`asyncpg`).
    * Implement an operational database engine writer service method: `async def save_telemetry_event(event: TelemetryEvent)`.
* **Dependencies:** Requires PostgreSQL container configurations from `docker-compose.yml`.

### 🟨 Task BE-202: Replace Stream Generator with Live DB Watchers
* **Target Directory:** `backend/app/network/router.py`
* **Objective:** Pivot the SSE `/stream` route from generating arbitrary mock data to querying the database or in-memory queues.
* **Requirements:**
    * Create an internal async publisher/subscriber queue (like `asyncio.Queue`).
    * Refactor the `stream_telemetry` function to read incoming messages natively pushed to the queue by your ingestion endpoints instead of running a standalone pseudo-random `while True` calculation loop.

---

## 🧠 PHASE 3: AI ROUTING & INFRASTRUCTURE MATRIX
*Focus: Connecting local inference pipelines and high-parameter cloud agent orchestration frameworks.*

### 🟦 Task AI-301: Connect Ollama Local Gemma 4 Client
* **Target Directory:** `backend/app/network/` or `backend/app/ai/`
* **Objective:** Wire up the actual local routing interface to query the local Gemma model.
* **Requirements:**
    * Write an asynchronous HTTP wrapper calling your local Ollama container (`POST http://ollama:11434/api/chat`).
    * Pass raw log vectors into Gemma 4 using structural system directives that strictly enforce JSON formatting schema constraints (`format="json"`).
    * Parse the JSON payload to drive the dynamic conditional routing logic (determining whether traffic `PASSED` or requires `ESCALATED` flags).
* **Dependencies:** Task BE-202 (The resulting parsed data matrix must feed into the live streaming queue).

### 🟦 Task AI-302: Implement LangGraph Multi-Agent Escalation Loop
* **Target Directory:** `backend/app/agents/`
* **Objective:** Build out the fallback cloud analysis layer using Fireworks AI API blocks for instances flagged as high-risk anomalies.
* **Requirements:**
    * Use LangGraph or CrewAI to construct a conditional state loop.
    * Build **Node A (CyberSec Specialist)**: Evaluates structural log payload attributes, anomalous server connection strings, and credential patterns.
    * Build **Node B (Anti-Fraud Specialist)**: Tracks bank routing metadata anomalies, high velocity volume transactions, and potential account mule setups.
    * Synthesize their findings into an itemized diagnostic narrative summary string.
* **Dependencies:** Task AI-301 (This agent network loop is explicitly triggered asynchronously when Gemma 4 flags `escalate: true`).

---

## 📊 DEVELOPMENT CONCURRENCY MATRIX

To prevent file conflicts and overlapping commits, assign tasks to team members based on this isolation mapping:

| Developer Target | Primary Workspace Assignee | Isolated Dependency Gate |
| :--- | :--- | :--- |
| **Frontend Dev A** | Features: `cyber-grid/*` | Consumes backend SSE streaming payload contracts. |
| **Frontend Dev B** | Features: `ledger-audit/*`, Shared UI components | Modifies app routing maps and global CSS configurations. |
| **Backend Dev A** | Data Layer, Ingestion APIs, Server Core | Manages models, database synchronization, and local queues. |
| **AI Specialist** | Ollama integrations, LangGraph pipelines | Focuses on agent loops inside `backend/app/agents/`. |

---

## 🏁 MILESTONE VALIDATION
The workspace is complete when a live packet payload target dropped into the backend API gateway triggers a local Gemma inference calculation, records the row state securely in PostgreSQL, routes complex alerts to cloud models, and reflects the updated data instantly on your Angular Dashboard UI via micro-fine Signals updates.

---

## Bugs

1. FE when switching between dashboards, the table is not loading the data.