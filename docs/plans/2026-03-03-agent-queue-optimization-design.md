# Agent Queue Optimization Design

Date: 2026-03-03
Owner: AidSec Engineering
Status: Approved for implementation

## 1) Context and Goal

The current Agent Queue flow is functionally complete but operationally noisy under load:
- Queue view mixes active work and history in one table.
- Large draft spikes can happen when multiple triggers enqueue overlapping tasks.
- Bulk draft operations can become expensive when executed as many single requests.
- There is no enforced retention policy for historical task records.

Goal: Make the queue operations-first, prevent duplicate draft generation, and keep queue data lean and reliable without re-platforming.

Primary success criteria:
1. No duplicate open drafts per lead (hard dedupe).
2. Queue page default shows active operations only.
3. Historical records automatically cleaned after 30 days.
4. Production behavior remains backward-compatible during rollout.

---

## 2) Current Architecture Summary

### Backend
- Task model: `AgentTask` in `aidsec_dashboard/database/models.py`.
- Queue list endpoint: `GET /tasks` in `aidsec_dashboard/api/routes/tasks.py`.
- Agent lifecycle endpoints: pull/heartbeat/complete in `aidsec_dashboard/api/routes/agent_tasks.py`.
- Task enqueue sources:
  - Campaign due processor (`/campaigns/process-due`) in `aidsec_dashboard/api/routes/campaigns.py`
  - Auto-followup trigger (`/campaigns/auto-followup`) in `aidsec_dashboard/api/routes/campaigns.py`
  - Telegram command path in `aidsec_dashboard/services/telegram_service.py`
- Draft output written in `complete_agent_task()` for `GENERATE_DRAFT` tasks.

### Frontend
- Agent Queue page: `frontend/src/app/(dashboard)/tasks/page.tsx`
- Dashboard summary widgets consume queue state from `agentTasksApi.listTasks()`.
- API client queue binding: `frontend/src/lib/api.ts`

---

## 3) Target Design

### 3.1 Queue Segmentation (Operations-first)

Introduce explicit queue modes:
- **Active Queue** (default): `pending`, `processing`, `retry-ready`
- **History**: `completed`, `failed`, `dead_letter`

Proposed endpoints:
- `GET /tasks/active?limit=&cursor=`
- `GET /tasks/history?status=&from=&to=&limit=&cursor=`
- Optional metrics endpoint: `GET /tasks/metrics`

`GET /tasks` remains for backward compatibility but is not the default frontend source.

### 3.2 Hard Dedupe Rules

Enforce dedupe in two places:

1) **At enqueue time** (campaign/auto-followup/telegram):
- Reject creating a new `GENERATE_DRAFT` task if an open task already exists for the same lead (`pending` or `processing`).
- Optionally scope by `(lead_id, campaign_id)` where campaign context exists.

2) **At complete time** (`complete_agent_task`):
- Before inserting into `email_history`, check if an open draft already exists for the lead (`status=draft`).
- If yes, mark task as completed with a dedupe result flag instead of creating another draft.

Outcome: no multiple open drafts for the same lead.

### 3.3 Retention Policy

Retention: 30 days for non-active task statuses.

Daily cleanup job:
- Delete tasks older than 30 days where status in (`completed`, `failed`, `dead_letter`).
- Never delete `pending`/`processing`/retry-eligible tasks.

---

## 4) Data Flow (Target)

1. Trigger creates task request.
2. Enqueue service checks hard dedupe guard.
3. If accepted, task enters `pending`.
4. Agent pulls task (`/agents/tasks/pull`), lease lock applied.
5. Agent heartbeats while processing.
6. Agent completes task.
7. Completion handler:
   - Applies dedupe guard before draft insert.
   - Writes one draft max per lead open state.
   - Finalizes task status.
8. Queue UI:
   - Active tab reads from `/tasks/active`
   - History tab reads from `/tasks/history`
9. Retention job purges old history rows daily.

---

## 5) Error Handling and Operational Signals

Add/standardize machine-readable error details:
- `task_conflict` (enqueue blocked due to open task)
- `draft_exists` (completion dedupe blocked extra draft)
- `lease_invalid`
- `max_attempts_exceeded`

UI behavior:
- Active queue highlights retry/dead-letter counts.
- History shows failure reason and attempt metadata.
- Dashboard cards use `/tasks/metrics` (or compact active + dead-letter aggregates).

---

## 6) Rollout Plan

### Phase A — Backend Compatibility First
- Add active/history endpoints.
- Add enqueue dedupe and completion dedupe checks.
- Keep current endpoints functioning.

### Phase B — Frontend Queue UX
- Switch queue page default to active mode.
- Add separate history tab with server-side pagination.
- Keep a temporary fallback to legacy list if needed.

### Phase C — Retention + Cleanup
- Enable daily retention job.
- Remove legacy mixed-list usage in frontend.
- Keep legacy endpoint for admin/debug only.

---

## 7) Testing Strategy

Must-pass tests:
1. Enqueue dedupe blocks duplicate open tasks for same lead.
2. Completion dedupe blocks second open draft creation.
3. Lease race: two agents cannot finalize same task.
4. Retry/backoff transitions behave correctly.
5. Retention deletes only old historical statuses.
6. Queue UI active tab contains no completed/dead rows.

Smoke checks after deploy:
- `GET /tasks/active` returns only active statuses.
- `GET /tasks/history` excludes active statuses.
- Draft queue count remains stable under repeated trigger runs.

---

## 8) Items to Remove / Simplify (YAGNI)

- Mixed-status default queue table in the primary operations view.
- Any high-volume client-side batch patterns that issue thousands of individual calls.
- Redundant frontend env variables not required for proxy architecture.

---

## 9) Accepted Product Decisions (from workshop)

- Queue scope: Active queue + separate history.
- Retention: 30 days.
- Dedupe policy: Hard dedupe (block duplicate open drafts per lead).

This document is approved as the baseline for implementation planning.
