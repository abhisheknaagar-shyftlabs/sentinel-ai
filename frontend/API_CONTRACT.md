# Sentinel AI — Backend API Contract

This document is the source of truth for the endpoints the **Sentinel AI frontend** expects.
Build these exactly (routes, field names, types) and the frontend will work with **zero code
changes** the moment the backend is live.

> The frontend currently runs on mock data. To point it at the real backend, set:
> ```bash
> # sentinel-frontend/.env.local
> VITE_API_BASE_URL=http://localhost:8000/api
> VITE_USE_MOCK_DATA=false
> ```
> Every route below is relative to `VITE_API_BASE_URL` (e.g. `/dashboard/summary` →
> `http://localhost:8000/api/dashboard/summary`).

---

## 1. Conventions (read first)

| Rule | Detail |
| --- | --- |
| **Base path** | All routes are prefixed by `VITE_API_BASE_URL` (default `/api`). |
| **Method + headers** | JSON only. Frontend sends `Content-Type: application/json`. |
| **Casing** | **camelCase** JSON keys, exactly as written here. The frontend does `response.json()` with no key transformation — `openPRsAtRisk` must be `openPRsAtRisk`, not `open_prs_at_risk`. |
| **Success** | Return HTTP `200` (or `204` for the PATCH). Body is the JSON described per endpoint. |
| **Errors** | Any non-`2xx` status makes the frontend show its Error state with a Retry button. Return `4xx`/`5xx` with any body. A JSON body like `{ "message": "..." }` is nice-to-have but not required. |
| **Enums** | String enums are **lowercase** and must match exactly (see §2). Sending an unknown value renders a neutral/grey fallback but won't crash. |
| **Numbers** | Plain numbers (not strings). `infraCostMonthly: 18240`, not `"18240"`. The frontend formats currency/percent itself. |
| **Timestamps** | ⚠️ See the note in §2 — several fields are **display strings** today (`"12m ago"`), not ISO dates. Read that before implementing. |
| **Auth** | See §3. A bearer token flow is recommended; the current frontend login is mocked and needs a small wiring change to use a real endpoint. |

---

## 2. Shared types & enums

These building blocks are reused across many endpoints.

### Enums (lowercase, exact match)

```
RiskLevel            = "low" | "medium" | "high" | "critical"
HealthStatus         = "healthy" | "degraded" | "unhealthy" | "unknown"
DeploymentConfidence = "safe" | "caution" | "blocked"
IncidentSeverity     = "sev1" | "sev2" | "sev3" | "sev4"
IncidentStatus       = "open" | "investigating" | "resolved" | "monitoring"
TrendDirection       = "up" | "down" | "flat"
ConnectionStatus     = "connected" | "disconnected" | "error" | "pending"
```

### `Trend` object (used by every stat that shows a % change chip)

```jsonc
{
  "direction": "up",        // TrendDirection — arrow shown
  "changePercent": 4,       // number — the % value shown
  "isPositive": true        // bool — TRUE = green chip, FALSE = red chip.
                            // NOTE: semantic, not directional. A cost going DOWN
                            // is isPositive:true (good). Incidents going UP is
                            // isPositive:false (bad). Backend decides good vs bad.
}
```

### `SeriesPoint` (used by line/bar charts)

```jsonc
{ "label": "Mon", "value": 78 }   // label = x-axis text, value = y-axis number
```

### ⚠️ Timestamp fields — important

Today the frontend prints these fields **verbatim** (no date parsing). To make integration
work immediately, return them as **short display strings**:

- Relative style: `"12m ago"`, `"2h ago"`, `"1d ago"`, `"30 seconds ago"`
- Clock style (logs): `"10:42:01"`
- Duration style (uptime): `"14d 6h"`
- Plain date (tech debt): `"2026-06-18"`

Affected fields: `timestamp`, `updatedAt`, `detectedAt`, `startedAt`, `lastCommit`,
`uptime`, `lastSyncedAt`.

> **Recommended (cleaner) alternative:** return proper **ISO 8601** timestamps
> (`"2026-07-02T10:42:01Z"`) and I'll switch the frontend to format them (there's already a
> `formatRelativeTime()` util ready). Tell me which you prefer — either works, but pick one
> so we're consistent.

---

## 3. Authentication (recommended — currently mocked)

The login screen currently fakes auth locally. For a real backend, implement:

### `POST /auth/login`
**Request body**
```jsonc
{ "email": "jordan.lee@acme.com", "password": "••••••" }
```
**Response `200`**
```jsonc
{
  "token": "jwt-or-session-token",
  "user": { "name": "Jordan Lee", "email": "jordan.lee@acme.com", "workspace": "Acme Engineering" }
}
```
**On bad credentials:** return `401`.

> Wiring note: this one needs a ~10-line change on the frontend (the login form calls the store
> directly right now). Ping me when the endpoint exists and I'll connect it + attach the token
> to the API client's `Authorization` header.

---

## 4. Dashboard

### `GET /dashboard/summary`
Aggregated overview shown on the landing dashboard.

**Response `200`**
```jsonc
{
  "stats": {
    "openPRsAtRisk": 3,
    "openPRsAtRiskTrend": { "direction": "down", "changePercent": 25, "isPositive": true },
    "containersHealthy": 46,
    "containersTotal": 48,
    "openIncidents": 1,
    "openIncidentsTrend": { "direction": "up", "changePercent": 100, "isPositive": false },
    "engineeringHealthScore": 87,
    "engineeringHealthTrend": { "direction": "up", "changePercent": 4, "isPositive": true },
    "infraCostMonthly": 18240,
    "infraCostTrend": { "direction": "down", "changePercent": 12, "isPositive": true },
    "deploymentConfidencePercent": 92,
    "deploymentConfidenceTrend": { "direction": "up", "changePercent": 3, "isPositive": true }
  },
  "developmentSnapshot": {
    "headline": "3 pull requests need review",
    "detail": "1 high-risk PR touches the payments retry path — flagged before merge.",
    "risk": "high"                       // RiskLevel
  },
  "productionSnapshot": {
    "headline": "notifications service degraded",
    "detail": "Memory leak in queue consumer, auto-restarted 2 minutes ago.",
    "health": "degraded"                 // HealthStatus
  },
  "executiveSnapshot": {
    "headline": "Engineering health at 87/100",
    "detail": "Up 4 points this month, driven by fewer rollback incidents.",
    "trend": { "direction": "up", "changePercent": 4, "isPositive": true }
  },
  "healthTrend": [                       // SeriesPoint[] — 7-day line chart
    { "label": "Mon", "value": 78 },
    { "label": "Sun", "value": 87 }
  ],
  "recentActivity": [                    // TimelineItem[]
    {
      "id": "act-1",
      "title": "AI generated a fix for PR #482",
      "description": "Suggested rate-limit guard for /webhooks/stripe",  // optional
      "timestamp": "12m ago",
      "tone": "success"                  // "neutral" | "success" | "warning" | "danger"
    }
  ]
}
```

---

## 5. Development Intelligence

### `GET /development-intelligence/summary`

**Response `200`**
```jsonc
{
  "stats": {
    "openPRs": 12,
    "openPRsTrend": { "direction": "up", "changePercent": 9, "isPositive": false },
    "highRiskPRs": 3,
    "avgDeploymentConfidence": 84,       // number (percent)
    "avgDeploymentConfidenceTrend": { "direction": "up", "changePercent": 2, "isPositive": true },
    "technicalDebtHours": 126,
    "technicalDebtTrend": { "direction": "down", "changePercent": 8, "isPositive": true }
  },
  "pullRequests": [
    {
      "id": "pr-482",
      "number": 482,
      "title": "Refactor payment retry logic",
      "author": "a.torres",
      "branch": "feat/payment-retry",
      "risk": "high",                    // RiskLevel
      "deploymentConfidence": 62,        // number (percent)
      "filesChanged": 14,
      "linesAdded": 320,
      "linesRemoved": 118,
      "status": "open",                  // "open" | "draft" | "merged"
      "updatedAt": "12m ago"
    }
  ],
  "technicalDebt": [
    {
      "id": "debt-1",
      "module": "billing/invoice-generator",
      "description": "Legacy PDF pipeline uses the deprecated v1 template engine.",
      "severity": "high",                // RiskLevel
      "estimatedHours": 32,
      "detectedAt": "2026-06-18"
    }
  ],
  "aiFixes": [
    {
      "id": "fix-1",
      "prNumber": 482,
      "title": "Add exponential backoff to payment retry loop",
      "description": "Current impl retries immediately, risking a thundering herd.",
      "status": "suggested",             // "suggested" | "applied" | "dismissed"
      "confidence": 91                   // number (percent)
    }
  ]
}
```

### `GET /development-intelligence/branches`
List of branches for the Branch Comparison dropdowns.

**Response `200`**
```jsonc
[
  { "name": "main", "lastCommit": "2h ago", "author": "a.torres", "isProtected": true },
  { "name": "feat/payment-retry", "lastCommit": "12m ago", "author": "a.torres" }
  // isProtected is optional
]
```

### `GET /development-intelligence/compare`
Compares two branches and returns a merge assessment.

**Query params**
| Param | Type | Example |
| --- | --- | --- |
| `base` | string (branch name) | `main` |
| `head` | string (branch name) | `feat/payment-retry` |

Full URL example:
`/development-intelligence/compare?base=main&head=feat/payment-retry`

**Response `200`**
```jsonc
{
  "base": "main",
  "head": "feat/payment-retry",
  "identical": false,                    // true = same commit → frontend shows "nothing to compare"
  "commitsAhead": 8,
  "commitsBehind": 2,
  "filesChanged": 3,
  "additions": 320,
  "deletions": 118,
  "risk": "high",                        // RiskLevel — overall merge risk badge
  "deploymentConfidence": 62,            // number (percent)
  "mergeScore": 58,                      // number 0–100 — the animated score ring
  "recommendation": "caution",           // "merge" | "caution" | "hold"
  "summary": "Rewrites the payment retry path with no backoff...",   // 1–2 sentence description
  "gains": [                             // string[] — "What you gain" bullets
    "Automatically retries transient payment failures instead of dropping them",
    "Adds a dedicated test suite for the retry path"
  ],
  "risks": [                             // string[] — "What you risk" bullets
    "No exponential backoff — a provider outage could trigger a thundering herd",
    "Changes money-critical code with no circuit breaker"
  ],
  "changedFiles": [
    {
      "path": "src/payments/retry.ts",
      "status": "modified",              // "added" | "modified" | "deleted" | "renamed"
      "additions": 164,
      "deletions": 72,
      "risk": "high"                     // RiskLevel
    }
  ]
}
```
**When `base === head`:** return `identical: true`, zeroed counts, empty arrays, `mergeScore: 100`,
`recommendation: "merge"`.

---

## 6. Production Intelligence

### `GET /production-intelligence/summary`

**Response `200`**
```jsonc
{
  "stats": {
    "containersHealthy": 46,
    "containersTotal": 48,
    "openIncidents": 1,
    "openIncidentsTrend": { "direction": "up", "changePercent": 100, "isPositive": false },
    "autoRecoveriesToday": 4,
    "avgRecoveryTimeMinutes": 2.4,       // number (may be decimal)
    "avgRecoveryTrend": { "direction": "down", "changePercent": 18, "isPositive": true }
  },
  "containers": [
    {
      "id": "c-1",
      "name": "api-gateway",
      "status": "healthy",               // HealthStatus
      "cpuPercent": 34,                  // number 0–100
      "memoryPercent": 58,               // number 0–100
      "uptime": "14d 6h",
      "restarts": 0
    }
  ],
  "logs": [
    {
      "id": "l-1",
      "timestamp": "10:42:01",
      "level": "error",                  // "info" | "warn" | "error" | "debug"
      "service": "media-transcoder",
      "message": "OOMKilled: container exceeded memory limit (1024Mi)"
    }
  ],
  "incidents": [
    {
      "id": "inc-1",
      "title": "notifications service degraded",
      "service": "notifications",
      "severity": "sev3",                // "sev1" | "sev2" | "sev3" | "sev4"
      "status": "monitoring",            // "open" | "investigating" | "resolved" | "monitoring"
      "rootCause": "Memory leak in queue consumer causing gradual OOM.",  // optional
      "autoRecovered": true,             // bool — shows the "auto recovered" badge
      "startedAt": "12m ago"
    }
  ]
}
```

---

## 7. Executive Intelligence

### `GET /executive-intelligence/summary`

**Response `200`**
```jsonc
{
  "stats": {
    "engineeringHealthScore": 87,
    "engineeringHealthTrend": { "direction": "up", "changePercent": 4, "isPositive": true },
    "deploymentReadiness": "safe",       // DeploymentConfidence: "safe" | "caution" | "blocked"
    "infraCostMonthly": 18240,
    "infraCostTrend": { "direction": "down", "changePercent": 12, "isPositive": true },
    "potentialMonthlySavings": 4900,
    "incidentsThisQuarter": 14,
    "incidentsTrend": { "direction": "down", "changePercent": 22, "isPositive": true }
  },
  "healthTrend": [                       // SeriesPoint[] — monthly line chart
    { "label": "Jan", "value": 72 },
    { "label": "Jul", "value": 87 }
  ],
  "healthDimensions": [                  // horizontal score bars
    { "label": "Deployment success rate", "score": 94 },   // score = number 0–100
    { "label": "Mean time to recovery", "score": 82 }
  ],
  "costBreakdown": [
    {
      "service": "Compute (EC2 / ECS)",
      "monthlyCost": 8640,
      "percentOfTotal": 47,              // number 0–100 (bar width)
      "trend": { "direction": "down", "changePercent": 8, "isPositive": true }
    }
  ],
  "costOptimizations": [
    {
      "id": "opt-1",
      "title": "Right-size over-provisioned ECS tasks",
      "description": "6 services are consistently under 20% CPU utilization.",
      "estimatedMonthlySavings": 2400,
      "effort": "low"                    // RiskLevel — reused as effort level
    }
  ],
  "incidentAnalytics": [                 // SeriesPoint[] — monthly bar chart
    { "label": "Jan", "value": 8 },
    { "label": "Jul", "value": 3 }
  ]
}
```

---

## 8. Integrations

### `GET /integrations`
Connection status of external tools.

**Response `200`**
```jsonc
[
  {
    "id": "github",                      // must be one of: "github" | "docker" | "prometheus" | "grafana"
                                         // (frontend maps id → icon)
    "name": "GitHub",
    "description": "Pull request reviews, risk analysis, and repository insights.",
    "category": "source-control",        // "source-control" | "containers" | "metrics" | "dashboards"
    "status": "connected",               // ConnectionStatus: "connected" | "disconnected" | "error" | "pending"
    "connectedAccount": "acme-engineering",  // optional
    "lastSyncedAt": "2 minutes ago"          // optional
  }
]
```

> **Optional (nice-to-have):** connect/disconnect actions currently just show a toast on the
> frontend. If you want them real, add `POST /integrations/{id}/connect` and
> `POST /integrations/{id}/disconnect` (both returning the updated `Integration`) and I'll wire
> the buttons. Not required for the demo.

---

## 9. Settings

### `GET /settings`
**Response `200`**
```jsonc
{
  "workspace": {
    "workspaceName": "Acme Engineering",
    "timezone": "America/New_York",
    "defaultBranch": "main"
  },
  "notifications": {
    "incidentAlerts": true,
    "prRiskAlerts": true,
    "weeklyDigest": true,
    "costAlerts": false,
    "notificationEmail": "oncall@acme.com"
  },
  "aiPreferences": {
    "autoFixEnabled": true,
    "autoRecoveryEnabled": true,
    "riskSensitivity": "balanced",       // "conservative" | "balanced" | "aggressive"
    "minConfidenceThreshold": 80         // number 0–100
  }
}
```

### `PATCH /settings/{section}`
Saves one settings section. `{section}` is one of: `workspace`, `notifications`, `aiPreferences`.

**Request body** = the object for that section (same shape as under `GET /settings`). Examples:

`PATCH /settings/workspace`
```jsonc
{ "workspaceName": "Acme Engineering", "timezone": "America/New_York", "defaultBranch": "main" }
```

`PATCH /settings/notifications`
```jsonc
{ "incidentAlerts": true, "prRiskAlerts": true, "weeklyDigest": true, "costAlerts": false, "notificationEmail": "oncall@acme.com" }
```

`PATCH /settings/aiPreferences`
```jsonc
{ "autoFixEnabled": true, "autoRecoveryEnabled": true, "riskSensitivity": "balanced", "minConfidenceThreshold": 80 }
```

**Response:** `200` or `204`. Body is ignored by the frontend (it shows a success toast and
refetches `GET /settings`).

**Validation** (frontend already enforces these; backend should too):
- `workspaceName` — min 2 chars
- `notificationEmail` — valid email
- `riskSensitivity` — one of the three enum values
- `minConfidenceThreshold` — integer 0–100

---

## 10. Endpoint summary

| # | Method | Route | Purpose |
| --- | --- | --- | --- |
| 1 | `POST` | `/auth/login` | Authenticate (recommended; currently mocked) |
| 2 | `GET`  | `/dashboard/summary` | Dashboard overview |
| 3 | `GET`  | `/development-intelligence/summary` | PRs, tech debt, AI fixes |
| 4 | `GET`  | `/development-intelligence/branches` | Branch list for comparison |
| 5 | `GET`  | `/development-intelligence/compare?base=&head=` | Branch merge assessment |
| 6 | `GET`  | `/production-intelligence/summary` | Containers, logs, incidents |
| 7 | `GET`  | `/executive-intelligence/summary` | Health, cost, incident analytics |
| 8 | `GET`  | `/integrations` | Integration connection status |
| 9 | `GET`  | `/settings` | Load all settings |
| 10 | `PATCH` | `/settings/{section}` | Save one settings section |

*(Optional extras mentioned inline: integration connect/disconnect.)*

---

## 11. How to test the integration

1. Backend runs (e.g. `http://localhost:8000`) and serves the routes above under `/api`.
2. In `sentinel-frontend/`, create `.env.local`:
   ```
   VITE_API_BASE_URL=http://localhost:8000/api
   VITE_USE_MOCK_DATA=false
   ```
3. Enable CORS on the backend for the frontend origin (Vite dev default `http://localhost:5173`).
4. `npm run dev` and open each page — every page has built-in **loading**, **error**, and
   **empty** states, so partial/failing endpoints degrade gracefully while you fill them in.

Match the JSON shapes above exactly and it works on first connect. Questions on any field →
ask, and I'll clarify or adjust the frontend.
