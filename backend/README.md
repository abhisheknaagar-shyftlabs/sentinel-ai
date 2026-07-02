# Sentinel AI — Backend

FastAPI backend for Sentinel AI, an AI-powered engineering control center (Development Intelligence, Production Intelligence, Executive Intelligence). The frontend is a separate, parallel effort built against mock data — this backend is being built independently to the same API contract.

## Status

| Step | Scope | Status |
|---|---|---|
| 1 | Foundation: config, logging, DB, Redis, JWT auth, health checks | ✅ Done |
| — | Continuum: AI orchestration layer (wraps the real `shyftlabs-continuum` SDK) | ✅ Done |
| 3a | GitHub repository integration (PAT auth, repos/PRs/diffs/commits) | ✅ Done |
| 3b | AI-powered PR review (executive summary, risk, deployment confidence, findings, fixes) | ✅ Done — live-verified against the real Smart Gateway |
| 3c | Risk analysis / deployment confidence as standalone endpoints | ⬜ Not started |
| 4a | Docker monitoring (containers, live stats, logs, safe restart) | ✅ Done — live-verified against the real local Docker Engine |
| 5a | Root Cause Analysis (diagnosis from live Docker state) | ✅ Done — live-verified with a real successful diagnosis (see below) |
| 6 | Incident Engine (lifecycle, timeline, reuses RCA + safe restart) | ✅ Done — live-verified end to end against real Docker + Postgres |
| 7 | Executive analytics: engineering health score (real formula) + AWS Cost Explorer integration | ✅ Done — health score live-verified; cost integration built for real, gracefully degrades without valid AWS credentials in this dev environment |
| 8 | Settings API (workspace / notifications / AI preferences) | ✅ Done |
| — | Frontend integration adapter layer (`/api/*`, camelCase, matches `frontend/API_CONTRACT.md` exactly) | ✅ Done — live-verified against the real frontend dev server, see below |
| — | Workspaces / RBAC | ⬜ Not started |
| — | `executive_summary` Continuum agent | ⬜ Placeholder only |

## Tech stack

Python 3.12+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2 (async), PostgreSQL, Redis, Alembic, PyJWT, bcrypt, pytest.

## Project layout

```
app/
  api/v1/            # routers -> validate input, call services, return responses (enveloped, snake_case)
    endpoints/       # health.py, auth.py, github.py, docker.py, incidents.py
    router.py        # aggregates endpoint routers under /api/v1
  api/frontend/      # adapter layer for the real frontend — see below (raw JSON, camelCase, under /api)
  config/            # Pydantic Settings (settings.py)
  core/              # logging, exceptions, response envelope — cross-cutting
  database/          # async engine/session, declarative base, get_db dependency
  models/            # SQLAlchemy ORM models (User, Workspace, Integration, TrackedRepository, AIReview, AIFix, Incident, IncidentContainer, IncidentEvent, UserSettings)
  schemas/           # Pydantic request/response models, incl. incident.py, camel.py (CamelModel base for the frontend adapter)
  repositories/      # data access layer (BaseRepository + per-model repos)
  services/          # business logic (AuthService, GitHubIntegrationService, PRReviewService, RootCauseAnalysisService, IncidentService, TechnicalDebtService, ExecutiveMetricsService, SettingsService)
  security/          # password hashing, JWT issue/verify, get_current_user, secret encryption
  middleware/        # request-ID + timing + structured access logs
  continuum/         # AI orchestration layer — see below
  agents/            # concrete AI agents, grouped by product module
    development/      #   PR review, risk analysis, etc.
    production/        #   root cause, incident response, etc.
    executive/          #   executive summaries (placeholder), health scoring, etc.
  integrations/      # external systems
    github/            #   typed REST client (repos/PRs/diffs/files/commits/branches/compare) — see above
    docker/            #   local Docker Engine client + service — see below
    aws/               #   AWS Cost Explorer client (boto3) — see below
    jira/, prometheus/, grafana/, redis/   # scaffolded, not yet implemented
  utils/time.py      # display-string timestamp formatters shared by the frontend adapter
  workers/, tasks/    # background job scaffolding (Celery-ready, unused yet)
  main.py             # FastAPI app factory — mounts both /api/v1 and /api (frontend adapter)
alembic/              # DB migrations (async-aware env.py)
tests/                # pytest — unit tests, no external services required
```

### Continuum — the AI orchestration layer

**This is a Continuum AI hackathon project: Continuum (the real `shyftlabs-continuum` SDK, not something we wrote) is the only AI runtime.** No router, service, or agent may import `anthropic`/`openai`/`google-genai` — the SDK itself is the only thing that ever touches a model:

```
FastAPI router -> Application Service -> ContinuumClient -> Agent -> Continuum SDK (AgentRunner) -> configured model -> typed response
```

- `continuum/base_agent.py` — `BaseAgent[InputT, OutputT]`, the class every domain agent subclasses. Takes a `continuum_client` in its constructor — never a model client.
- `continuum/registry.py` — `AgentRegistry` + `@register_agent("name")` decorator for self-registration. Unchanged since Step 3a.
- `continuum/client.py` — `ContinuumClient`, the only file in the app that imports `continuum.agent`/`continuum.core`:
  - `run_agent(name, input_data)` / `run_workflow(names, input_data)` / `health_check()` / `register_agent()` — the same registry-dispatch API services call, now backed by the real SDK. Returns a typed `AgentExecutionResult` (`success`, `data`, `error`, `error_type`, `duration_ms`) — no hand-rolled retry loop anymore, since the SDK's own `AgentRunner`/`RunnerConfig` already retries and circuit-breaks internally.
  - `run_prompt(agent_name, instructions, input_text, output_schema=None, model=None)` — the one method domain agents call to actually reach a model. Internally builds a `continuum.agent.BaseAgent` + runs it via `AgentRunner`, with memory/session/Langfuse all disabled (`ContainerConfig(enable_memory=False, enable_session=False, enable_langfuse=False)`) since Sentinel's calls are single-shot and stateless — no Redis/Qdrant/Langfuse needed just to run a completion. Maps the SDK's own exception hierarchy (`AgentTimeoutError`, `AgentError`, …) and its `structured_output_error` field into Sentinel's own `ContinuumTimeoutError` / `ContinuumUnavailableError` / `MalformedResponseError`.
- `continuum/dependencies.py` — FastAPI DI: `Depends(get_continuum_client)`.

Model selection is entirely the Continuum SDK's concern, via its own env vars (not `app/config/settings.py`) — see `.env.example`. This hackathon's shared **Smart Gateway** (`SMART_GATEWAY_URL=https://continuum.shyftops.io/v1` + `SMART_GATEWAY_API_KEY`) routes every model call through one endpoint regardless of provider, so no individual OpenAI/Anthropic/Gemini key is needed.

Adding a new agent (the reference pattern is `app/agents/development/pr_review_agent.py`): define `Input`/`Output` Pydantic models (no `dict`/`Any` in the output — see `app/agents/development/schemas.py`), write its prompt in a dedicated `prompts.py` next to it (never inline large prompt strings in the agent), subclass `BaseAgent`, call `self.continuum_client.run_prompt(..., output_schema=YourOutput)` in `run()`, decorate the class with `@register_agent("your_agent_name")`, and add the import to `app/agents/__init__.py`. It's now callable via `continuum_client.run_agent("your_agent_name", input_data)` with no other wiring — this is exactly how PR review, and every future agent (root cause, executive summary, recovery recommendation), works.

### AI-powered PR review (Step 3b)

`POST /api/v1/github/repositories/{repository_id}/pulls/{pr_number}/review` — the first complete AI feature. Flow: validate the user owns the tracked repo -> re-fetch the PR's latest metadata/diff/files/commits live from GitHub (via the existing `GitHubIntegrationService`, no GitHub logic duplicated) -> run `pr_review` through `ContinuumClient` -> persist a summary row -> return the full structured review.

- `app/agents/development/schemas.py` — `PRReviewInput` and the 12-section `PRReviewOutput` (`ExecutiveSummary`, `RiskAssessment`, `DeploymentConfidence`, `TechnicalDebt`, `Finding` lists for bugs/security/performance/maintainability, `BreakingChangeAssessment`, suggested improvements, `SuggestedFix` list, and an `approve` / `approve_with_changes` / `request_changes` `Recommendation`).
- `app/models/review.py` — `AIReview` (table `ai_reviews`): `repository_id`, `pull_request_number`, `review_timestamp`, `summary`, `risk_score`, `deployment_confidence`, `recommendation`, `technical_debt_summary`. Deliberately does **not** store the diff or any other GitHub content — that's always re-fetched live, this table exists purely for historical review tracking.
- `app/services/pr_review_service.py` — orchestrates the above and maps Continuum failures to the standard envelope: malformed structured output -> 422, Continuum timeout -> 504, Continuum/model unavailable -> 503. GitHub-side failures (bad token, PR not found) are already handled by `GitHubIntegrationService`, reused as-is.

### GitHub integration

Connect via a GitHub Personal Access Token — no OAuth app, no Continuum involvement (this is data fetching, not an AI capability).

- `integrations/github/client.py` — `GitHubClient`, a typed async wrapper over the GitHub REST API (auth, list repos, get repo, list/get PR, PR diff, PR files, PR commits). Takes a `transport` param for test injection (`httpx.MockTransport`).
- `integrations/github/schemas.py` — GitHub-shape domain models (`GitHubUser`, `GitHubRepo`, `GitHubPullRequestSummary/Detail`, `GitHubPullRequestFile`, `GitHubCommit`), decoupled from GitHub's raw JSON.
- `integrations/github/exceptions.py` — `GitHubAuthError` / `GitHubNotFoundError` / `GitHubRateLimitError` / `GitHubAPIError`, mapped to the app's standard `AppException` subclasses in `services/github_service.py`.
- `models/integration.py` + `models/repository.py` — `Integration` (one row per connected PAT; token stored via `security/encryption.py`, Fernet, key derived from `JWT_SECRET_KEY` — never a new secret to manage) and `TrackedRepository` (repos explicitly opted into tracking under an integration). PRs/diffs/commits are always fetched live from GitHub, never persisted.
- API: `POST /api/v1/github/integrations` (connect + validate token) · `GET/DELETE .../integrations{/id}` · `GET/POST .../integrations/{id}/repositories` (list available / track one) · `GET /api/v1/github/repositories` (tracked) · `GET .../repositories/{id}/pulls{,/{n},/{n}/diff,/{n}/files,/{n}/commits}` · `POST .../repositories/{id}/pulls/{n}/review` (AI review, see below).

### Docker monitoring (Phase 4a)

Monitors the **local** Docker Engine only — Sentinel backend, frontend, Postgres, Redis, and demo services all run as containers on the same EC2 host. No remote Docker, Kubernetes, or ECS support (the schemas are shaped so that's addable later without a redesign, but nothing here assumes it). Pure data collection — no AI reasoning, no Continuum involvement, nothing persisted; everything is fetched live on every call so a future Root Cause Analysis Agent always sees current state.

- `integrations/docker/client.py` — `DockerClient`, a thin async wrapper over the official `docker` SDK (`docker.from_env()`), never the CLI. Every SDK call is blocking, so it's offloaded via `asyncio.to_thread`. Takes an injectable `docker_client` param for test injection, same pattern as `GitHubClient`'s `transport` param.
- `integrations/docker/schemas.py` — `ContainerSummary` (list-weight metadata), `ContainerDetail` (summary + mounts + an embedded live stats snapshot), `ContainerStats` (CPU %, memory usage/limit/%, network RX/TX, block I/O), `ContainerLogs` (parsed into timestamped `ContainerLogEntry` lines, not a raw blob) — designed so the future RCA agent can consume them directly.
- `integrations/docker/service.py` — `DockerMonitoringService`: does all the raw-stats-dict-to-typed-model math (Docker's own CPU%/memory formulas, RFC3339Nano timestamp parsing including the `0001-01-01` "never started" zero-value), and maps `DockerError` subclasses to the app's standard `AppException`s (not found → 404, permission denied → 403, timeout → 504, daemon unavailable → 503).
- API: `GET /api/v1/docker/containers` (list, no live stats) · `GET .../containers/{id}` (metadata + mounts + one stats snapshot) · `GET .../containers/{id}/stats` (just live stats, for fast polling) · `GET .../containers/{id}/logs?tail=&timestamps=&limit=` · `POST .../containers/{id}/restart` (safe restart only — SIGTERM then SIGKILL after a grace period, never kill/remove/prune).

### Root Cause Analysis (Phase 5a)

`POST /api/v1/docker/containers/{id}/analyze` — diagnosis only, never restarts anything (that's a future Safe Recovery phase). The agent never talks to Docker itself: `app/services/root_cause_service.py` collects context entirely through the existing `DockerMonitoringService` (`get_container()` for metadata + stats, `get_container_logs()` for recent logs), then runs it through Continuum's `root_cause` agent.

- `app/agents/production/schemas.py` — `RootCauseAnalysisInput` **embeds `ContainerDetail` and `ContainerLogs` directly** from `app/integrations/docker/schemas.py` rather than redefining parallel fields — zero duplication of what Docker monitoring already collects. Output: `RootCauseAnalysisResponse` (`IncidentSummary` with severity + business impact, `RootCause` with typed `Evidence` list + a `ConfidenceScore`, `RecoveryPlan` with recommended actions, an `auto_restart_safe` flag + rationale, and a `requires_human_intervention` flag — shaped so a future Safe Recovery phase can consume it directly).
- `app/agents/production/prompts.py` — formats container metadata, live stats, and recent logs (deduped nothing yet — see note below) into the diagnostic prompt.
- Logging includes `docker_collection_ms` (time spent gathering Docker state) separately from `continuum_latency_ms` (time spent on the model call), plus `total_duration_ms` and success/failure — exactly so slow Docker calls and slow model calls are distinguishable in the logs.
- **Live-verified, including a real successful diagnosis.** Early manual testing saw the model call time out twice (~185s each) against a container with very repetitive logs; a later run against a different (healthy) container succeeded and returned a genuinely well-reasoned analysis — correctly identified no real failure, gave a 75% confidence score, and correctly recommended *against* an automatic restart since the container was healthy. Both the pipeline and the model's judgment are proven live now.

### Incident Engine (Phase 6)

The canonical production object — Sentinel no longer thinks in terms of "analyze this container," it thinks in terms of incidents with a lifecycle. Fully additive: reuses `DockerMonitoringService` and `RootCauseAnalysisService` as black boxes, duplicating neither Docker access nor AI logic nor restart logic.

- **Lifecycle**: `open → investigating → analyzed | recovery_available → resolved`. An incident lands on `recovery_available` only if the RCA agent's `recovery_plan.auto_restart_safe` came back `true`; otherwise it stops at `analyzed` and waits for a human. `/recover` is rejected with 409 unless the incident is in `recovery_available`.
- `app/models/incident.py` — `Incident` (title, summary, severity, status, resolved_at, root cause summary/confidence, recovery recommendation/executed/result) plus two child tables: `IncidentContainer` (a **snapshot** of each affected container's id/name/image at creation time — Docker state is live and can change or disappear, so this is durable evidence, not a live reference) and `IncidentEvent` (the timeline: `incident_created`, `analysis_started/completed/failed`, `recovery_started/completed/failed`, `resolved`).
- `app/services/incident_service.py` — the state machine. `analyze_incident()` calls `RootCauseAnalysisService.analyze_container()` on the incident's primary affected container (first in the list — multi-container aggregation is a deliberate non-goal for this phase) and reduces its `RecoveryPlan` into a status transition. `recover_incident()` calls `DockerMonitoringService.restart_container()` directly — same safe-restart implementation Docker Monitoring already exposes at `POST /docker/containers/{id}/restart`, not a second one.
- API: `GET /api/v1/incidents` · `GET /api/v1/incidents/{id}` · `POST /api/v1/incidents` (collects live Docker metadata for each `container_ids` entry as evidence) · `POST /api/v1/incidents/{id}/analyze` · `POST /api/v1/incidents/{id}/recover`.
- **Live-verified end to end** against real Postgres (not just SQLite tests) and the real local Docker Engine: created an incident against the real `backend-redis-1` container, ran a real analysis (the model correctly judged the healthy container didn't need restarting), and confirmed `/recover` correctly refused with 409 given the resulting `analyzed` status — the safety gate holds under real conditions, not just in mocks.

### Engineering health score & AWS cost (Step 7)

- `app/services/executive_service.py` — `ExecutiveMetricsService.compute_engineering_health_score()`: a real (first-pass, documented-as-unvalidated) weighted formula — 40% incident resolution rate + 35% container health % + 25% average PR deployment confidence, each sourced from real `IncidentRepository`/`DockerMonitoringService`/`AIReviewRepository` data, defaulting to 100 when there's no data yet rather than fabricating a number.
- `app/integrations/aws/` — `AWSCostClient` wraps `boto3`'s Cost Explorer (`get_cost_and_usage`, grouped by service, current month, `us-east-1` since Cost Explorer is only reachable there regardless of workload region). Built for real, not mocked — but **this dev environment has no valid AWS credentials**, so it gracefully degrades to a zero `CostSummary` rather than crashing; every consumer (executive summary, dashboard) treats `AWSCredentialsError`/`AWSUnavailableError` as "no cost data yet," not a hard failure.
- Cost optimization suggestions (`/api/executive-intelligence/summary`'s `costOptimizations`) are a documented heuristic — the top 3 costliest AWS services with an estimated 15% savings — since there's no CloudWatch utilization integration to back a precise number. Flagged clearly in the response `description` text, not presented as more precise than it is.

### Technical debt & AI fixes tracking

- `app/models/ai_fix.py` / `app/repositories/ai_fix_repository.py` — `AIFix` rows are persisted as a side effect of `PRReviewService.review_pull_request()` from the review's own `code_fix_suggestions` — no separate AI call, no duplicated logic.
- `app/services/technical_debt_service.py` — derives technical debt items directly from already-persisted `AIReview.technical_debt_summary` text (skipping trivial/empty values), bucketing severity and estimating hours from the review's own `risk_score`. Deliberately **not** a second Continuum agent — every PR review already produces real AI-written technical debt commentary, so a second call would be redundant.

### Frontend integration adapter layer

The real frontend (`frontend/`, see its own `API_CONTRACT.md`) expects flat, camelCase, unenveloped JSON — the opposite of `/api/v1`'s `{success, data, message}` envelope and snake_case convention. Rather than change any stable `/api/v1` behavior, this is a wholly separate, additive package:

```
router -> service (mostly the existing /api/v1 services and repositories, reused as black boxes) -> app/api/frontend/*.py -> CamelModel response
```

- `app/schemas/camel.py` — `CamelModel`, a Pydantic base with `alias_generator=to_camel`. **Gotcha**: `to_camel` doesn't know multi-letter acronyms like "PR" are one unit (`open_prs` → `openPrs`, not `openPRs`) — every field with an embedded acronym needs an explicit `Field(serialization_alias="openPRs")` override; grep the contract carefully for these rather than trusting the generator.
- `app/utils/time.py` — the contract's timestamp fields are **display strings**, not ISO dates (`"12m ago"`, `"10:42:01"`, `"14d 6h"`, `"2026-06-18"`) — `format_relative_time()` / `format_clock_time()` / `format_duration_since()` / `format_plain_date()` cover the four styles the contract calls for.
- `app/api/frontend/auth.py`, `integrations.py`, `settings.py`, `development.py`, `production.py`, `executive.py`, `dashboard.py` — one file per contract section, aggregated by `app/api/frontend/router.py` and mounted at `/api` in `app/main.py` (alongside, not instead of, `/api/v1`). Each reuses existing services/repositories directly:
  - **Development** (`/development-intelligence/summary|branches|compare`) — real tracked-repo PRs; runs a real Continuum PR review per open PR only if no review from the last 24h is already persisted (running one per page load would make the page unusable — documented deviation from a literal "always run a fresh review" reading).
  - **Production** (`/production-intelligence/summary`) — real container list + per-container live stats/logs from `DockerMonitoringService`, real incidents from `IncidentRepository`; log `level` is inferred from message text (Docker doesn't structure this), incident severity/status are remapped from Sentinel's own enums to the contract's (`critical→sev1`...`low→sev4`; `analyzed`/`recovery_available`→`monitoring`).
  - **Executive** (`/executive-intelligence/summary`) — health score + AWS cost as above; `healthTrend` is a single current-day point, not a real multi-month series, since no historical health-score snapshots are persisted yet (documented simplification, not silently faked history).
  - **Dashboard** (`/dashboard/summary`) — the landing-page aggregate; composes the other three adapters' underlying data sources directly rather than calling their HTTP endpoints, and never triggers a fresh AI review (cached reviews only) since it has to stay fast.
  - **Settings** (`/settings`, `PATCH /settings/{section}`) — backed by a new single-table `UserSettings` model (workspace/notifications/AI-preference columns), one row per user, created on first read.
  - **Integrations** (`/integrations`) — only returns GitHub and Docker, both real; Prometheus/Grafana are omitted entirely rather than faked, since neither is implemented.
- **Live-verified against the real frontend dev server**, not just pytest: `frontend/.env.local` pointed at this backend with `VITE_USE_MOCK_DATA=false`, CORS preflight + actual cross-origin fetch confirmed from `localhost:5173`, and every response checked field-by-field against the frontend's own TypeScript interfaces (`src/features/*/types/index.ts`) rather than just the markdown contract.

## Local development

Requires SSH access to `github.com/shyftlabs/continuum` (private repo) — `pip install` pulls the SDK straight from git.

```bash
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then add SMART_GATEWAY_API_KEY (ask a teammate) to get real AI reviews
docker compose up -d postgres redis
./.venv/bin/alembic upgrade head
./.venv/bin/uvicorn app.main:app --reload
```

Without `SMART_GATEWAY_API_KEY` set, the app still runs fully — PR review requests fail cleanly with a 503 ("The AI provider is currently unavailable") instead of a real review, since Continuum can't reach a model.

- API docs: `http://127.0.0.1:8000/docs`
- Liveness: `GET /health`
- Readiness (checks DB + Redis): `GET /api/v1/health/ready`
- Auth: `POST /api/v1/auth/register|login|refresh`, `GET /api/v1/auth/me`

Local Postgres runs on **port 5433** (not 5432) to avoid clashing with any Postgres already running on this machine — see `docker-compose.yml`.

### Running against the real frontend

```bash
# in frontend/
cat > .env.local <<'EOF'
VITE_API_BASE_URL=http://localhost:8000/api
VITE_USE_MOCK_DATA=false
EOF
npm install && npm run dev   # -> http://localhost:5173
```

`CORS_ORIGINS` in `.env`/`app/config/settings.py` already includes `http://localhost:5173` and `http://localhost:3000`.

## Tests

```bash
./.venv/bin/pytest -q
```

All tests run against SQLite in-memory fixtures — no Docker/Postgres/Redis required to run the suite. 134 tests passing as of the frontend integration work.

## Conventions

- **Response envelope** — every endpoint returns `{success, data, message, timestamp}` or `{success, error: {code, message}}` (`app/core/responses.py`).
- **Errors** — raise a subclass of `AppException` (`app/core/exceptions.py`); handlers convert it to the error envelope automatically. Never let internal exceptions/stack traces reach the client.
- **Layering** — routers never contain business logic. Routers call services; services call repositories; repositories talk to the ORM.
- **AI capabilities** — always go through Continuum (see above), never a direct LLM SDK call from a service or router.
