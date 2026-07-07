# 📡 RDNA AI GUARD // FRONTEND_STATION

This is the control deck for RDNA AI Guard. It leverages **Angular 19+**, native fine-grained **Signals**, and **RxJS event stream pipelines** to capture real-time security alerts without rendering degradation.

---

## 🏗️ ARCHITECTURE // FEATURE-DRIVEN DESIGN (FDD)

To maintain a scalable enterprise footprint, this frontend follows a strict **Feature-Driven Design** topology. Code is organized explicitly around business domain capabilities rather than shared technical types (e.g., placing all services or components in giant shared global directories is prohibited).

### Workspace Folder Layout
```text
src/app/
├── core/                         # Global, immutable singletons (guards, interceptors)
├── shared/                       # Dumb UI UI atoms, pipes, generic layouts
└── features/                     # Distinct, autonomous business-domain engines
    ├── cyber-grid/               # FEATURE: Packet inspection, threat graphs, IP traces
    │   ├── components/
    │   ├── data-access/          # API services, SSE event streams
    │   └── utils/
    ├── ledger-audit/             # FEATURE: Real-time fraud tracking, cash loops
    │   ├── components/
    │   ├── data-access/
    │   └── store/                # Dedicated Feature SignalState
    └── dashboard-shell/          # FEATURE: Nav, grid wrappers, shell layout

```

### Core Architecture Rules

1. **Isolation:** Features must never deeply import private components from other features. Cross-feature data propagation must happen exclusively via shared services or unified global store states.
2. **Data-Access Separation:** Component files must strictly render views. Raw HTTP streaming fetching, WebSocket listeners, and transformer utilities belong within the local `data-access/` layer.

---

## 🚀 STARTUP PROTOCOL

### 1. Build Compilation

Navigate to the frontend container and unpack package blueprints:

```bash
cd frontend
npm install

```

### 2. Activate Station

Boot up the local dev server matching the specified CORS allowances configuration:

```bash
ng serve --port 4200

```

Open up your secure browser layout to: **`http://localhost:4200`**

---

## ⚡ TELEMETRY CONSUMPTION SPECIFICATION

To consume the real-time pipeline from the FastAPI matrix, initialize a stream within your feature's `data-access` service matching this framework pattern:

```typescript
import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TelemetryStreamService {
  readonly latestEvent = signal<any>(null);

  connectTelemetryStream(): void {
    const stream = new EventSource('http://localhost:8000/api/v1/telemetry/stream');
    
    stream.addEventListener('telemetry', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      this.latestEvent.set(data); // Micro-fine signal node update skipping dirty component checks
    });
  }
}
