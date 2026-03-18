# Feature Landscape: Async PDF Export with Progress Feedback

**Domain:** Async background job UX — file generation with in-page progress
**Researched:** 2026-03-16
**Confidence:** HIGH (based on codebase analysis + established async UX patterns)

---

## Context

The current PDF export is a plain anchor tag (`<a :href="pdfUrl">`) that navigates to a Django view
which blocks the request for the full WeasyPrint render duration (~5-30 seconds). The browser tab
freezes, there is no feedback, and the user cannot do anything else in the UI during that time.

The target flow (from PROJECT.md) is:

```
Export button click
  → POST /api/export-jobs/          (create job, immediate response with job_id)
  → GET  /api/export-jobs/<id>/     (poll for status + progress %)
  → status == "done"
  → GET  /api/export-jobs/<id>/result/  (trigger file download)
```

All features below are evaluated in terms of this flow and this codebase.

---

## Table Stakes

Features the user expects. Missing any of these makes the async export feel broken or worse than
the synchronous fallback.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Immediate button state change | User needs to know their click was received | Low | Button changes to "Generating..." or shows spinner immediately on click; disable re-click |
| Progress bar with numeric % | Users expect visual feedback proportional to actual work | Medium | Requires Celery task to report progress at meaningful stages (not just 0% → 100%) |
| Auto-download when done | If the user must manually navigate somewhere to get the file, the UX is worse than a direct link | Low | `window.location.assign(resultUrl)` or invisible anchor click when polling sees `status=done` |
| Error message on failure | Silent failure is worse than the synchronous version | Low | Show a message in-page when `status=failed`; do not leave user with a stalled bar |
| Button reset after completion | Button must return to clickable state after download or error | Low | User may want to re-export after editing; a stuck "Generating..." button forces a page reload |
| Poll timeout / stale job detection | Polling must stop eventually even if the worker dies | Low | If polling runs for >120s with no progress change, treat as failed |
| Correct filename on download | PDF must have the same sanitized filename as the synchronous version | Low | Current filename logic is in `meal_plan_pdf` view; replicate in async task |
| Authentication enforcement on all endpoints | POST/GET/result endpoints must require login | Low | Consistent with all other API endpoints in this app |
| 404 on unknown job_id | Polling a non-existent job should return 404, not 500 | Low | Standard DRF behavior if using a model-backed ViewSet |

---

## Differentiators

Features that make the async experience noticeably better than the synchronous version, or better
than a naively-implemented async version.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Granular progress stages (not just 0→100) | Users can see that work is actually happening; "25% - building context", "60% - rendering HTML", "90% - writing PDF" is far more reassuring than a bar that sits at 0% then jumps to 100% | Medium | Requires the Celery task to call `update_state()` at 3-5 meaningful checkpoints in the WeasyPrint pipeline |
| Non-blocking UI during export | User can continue editing the meal plan while the PDF generates in the background | Low | This is the core value of async; automatically achieved if the progress bar is in-page (not a blocking modal) without disabling the rest of the UI |
| Visual indicator in PageHeader matching existing sync UX | The export status can use the same `syncStatus` visual language (`saved` / `pending` / `error`) that already exists in `PageHeader.vue` and `StickyBar.vue` | Low | Consistency with the existing design system; low implementation cost |
| Extensible job model | Future long-running operations (BLS import, bulk operations) can reuse the same `BackgroundJob` model and polling endpoint without schema changes | Medium | Requires `job_type` field and generic `progress` / `status` / `result_file` fields rather than PDF-specific columns |
| Job expiry / file cleanup | Generated PDF files should be deleted from storage after a short TTL (e.g. 10 minutes) to avoid unbounded disk usage | Medium | Celery beat periodic task or Django management command; important for production deployments |

---

## Anti-Features

Things to deliberately NOT build in this milestone. These would add complexity without proportional
user value, or conflict with the stated scope.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| WebSockets or Server-Sent Events for push updates | The export takes 5-30 seconds; polling at 1-2s intervals is functionally equivalent and requires zero infrastructure additions | Use polling (`setInterval`); PROJECT.md explicitly rules out WebSockets/SSE |
| Job history UI ("Your recent exports") | No user requirement exists; this is a single-user app and jobs are ephemeral | Store jobs in the DB for polling purposes only; do not expose a list endpoint or history view |
| Multi-user job isolation / per-user access control | PROJECT.md explicitly defers this; "single-user app for now" | If a job_id is a UUID, it is effectively unguessable; no ownership field needed in v1 |
| Cancel job button | Cancelling a Celery task mid-flight is non-trivial (requires `CELERY_TASK_ALWAYS_EAGER` guards, `app.control.revoke`, and race condition handling); the window is 5-30 seconds | If user wants to stop, they can ignore the result; the file is cleaned up automatically |
| Retry button with automatic re-submission | Adds frontend state machine complexity; the user can simply click Export again after an error | Reset button state on error; user re-clicks export manually |
| Progress bar on the meal plan list page | Export is triggered from the detail page; adding list-page awareness requires cross-page state management (localStorage events or BroadcastChannel) | Scope to the detail page where the export is initiated |
| Streaming the PDF to the browser as it generates | WeasyPrint does not support streaming output; it renders the full PDF in memory before returning | Deliver the completed file via the result endpoint after polling confirms `status=done` |
| Parallel exports (multiple jobs per plan at once) | No user need; adds job deduplication complexity | Disable the export button while a job is in-flight for this plan |
| Celery task result backend for progress (celery-progress library) | The project uses a `BackgroundJob` Django model as the source of truth; a separate Celery result backend (Redis-backed) would create two stores to keep in sync | Write progress to the `BackgroundJob` model from inside the task; poll the Django API, not Celery directly |

---

## Feature Dependencies

```
POST /api/export-jobs/ (create)
  requires: BackgroundJob model with status/progress fields
  requires: Celery + Redis wired into Django settings
  requires: Celery task that wraps existing get_meal_plan_context + WeasyPrint logic

GET /api/export-jobs/<id>/ (poll)
  requires: BackgroundJob model
  requires: POST endpoint (job must exist before polling)

GET /api/export-jobs/<id>/result/ (download)
  requires: BackgroundJob model with result_file field
  requires: Celery task to write the PDF to Django storage (FileField)
  requires: poll endpoint confirming status=done before download is triggered

Progress bar Vue component
  requires: poll endpoint returning { status, progress }
  requires: export button replaced from <a href> to @click handler
  requires: auto-download trigger when status=done

Granular progress stages (differentiator)
  requires: Celery task calling task.update_state() at checkpoints
  requires: BackgroundJob.progress being updated from those state changes

Job expiry / file cleanup (differentiator)
  requires: result_file stored via Django FileField (not streamed inline)
  requires: Celery beat OR a management command (adds scheduling complexity)
```

---

## MVP Recommendation

Prioritize this exact set — it delivers the complete async UX without any scope creep:

1. **BackgroundJob model** — `status` (pending/running/done/failed), `progress` (0-100 integer), `result_file` (FileField), `job_type` (for extensibility), `created_at`
2. **Celery task** — wraps existing `get_meal_plan_context` + WeasyPrint logic; updates `BackgroundJob.progress` at ~4 checkpoints (0%, 25%, 70%, 95%); saves PDF to `result_file` on completion; sets `status=done` or `status=failed`
3. **API endpoints** — `POST /api/export-jobs/` (create + dispatch task), `GET /api/export-jobs/<id>/` (poll), `GET /api/export-jobs/<id>/result/` (download redirect or file response)
4. **Vue progress bar component** — replaces the `<a href>` in `PageHeader.vue`; polls at 1.5s intervals; auto-triggers download on `status=done`; shows error message on `status=failed`; resets button state after completion or error
5. **Docker Compose additions** — Redis service + Celery worker container

**Defer:**
- Job expiry / file cleanup: add as a follow-up task; accept unbounded file growth in v1 or add a simple TTL in the task itself (delete file after serving)
- `job_type` filtering: add the field to the model but do not build a filtered list endpoint

---

## Progress Granularity Design

The Celery task for WeasyPrint has a natural pipeline that maps to progress checkpoints:

| Stage | Progress % | What Happens |
|-------|-----------|--------------|
| Task received by worker | 5% | Job created; task dispatched; update to `running` |
| Context built (`get_meal_plan_context`) | 25% | Database queries complete |
| Template rendered to HTML string | 60% | `render_to_string` complete |
| WeasyPrint HTML object created | 75% | `weasyprint.HTML(string=...)` initialized |
| PDF bytes generated | 90% | `html.write_pdf()` returned |
| File saved to storage | 100% → `done` | `result_file.save()` complete |

This gives the user a progress bar that moves meaningfully at each stage rather than sitting at 0%
for 25 seconds and then jumping to 100%.

---

## Polling Behavior Specification

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Poll interval | 1500ms | Fast enough to feel responsive; slow enough not to hammer the server |
| Max poll duration | 120s | 4x the worst-case WeasyPrint render time; if still running, treat as failed |
| Poll on tab visibility | Only when tab is visible | Use Page Visibility API to pause polling when user switches tabs; resume on return |
| Backoff on repeated errors | Linear: +500ms per consecutive poll error, max 5s | Network hiccup should not cause permanent failure |

---

## Error Handling Specification

| Error Condition | Behavior | User Sees |
|-----------------|----------|-----------|
| POST /api/export-jobs/ fails (4xx/5xx) | Do not start polling; reset button state immediately | "Export failed. Please try again." |
| Celery worker dies mid-task | Task status stays `running`; polling timeout triggers after 120s | "Export timed out. Please try again." |
| Task raises an exception | Task catches exception, sets `status=failed`, stores error message in `BackgroundJob.error_message` | "Export failed: [message]" or generic if no message |
| Result file missing when status=done | GET /result/ returns 404; frontend shows error | "Download failed. Please try again." |
| Network error during polling | Increment error counter; backoff; surface error if >5 consecutive failures | "Connection lost. Retrying..." |
| User navigates away mid-export | Polling stops (component unmounts, `clearInterval`); job continues in background | No UI feedback (job is headless); file is generated but user is gone |

---

## Sources

- Project context: `/home/orchid/projects/meal-plan-analyzer-opencode/.planning/PROJECT.md`
- Codebase analysis: `PageHeader.vue`, `MealPlanDetailApp.vue`, `StickyBar.vue`, `views.py` (`meal_plan_pdf`)
- Existing patterns: `syncStatus` / `syncMessage` state pattern in detail app; `ConfirmDeleteModal` pattern for inline UI; `fetch`-based API calls with CSRF token injection
- Established async UX conventions: polling at 1-2s intervals for jobs in the 5-60s range is standard practice (GitHub Actions, Stripe webhook processing, Heroku deploys); source: engineering knowledge, confidence HIGH
- Celery task state reporting: `task.update_state(state='PROGRESS', meta={'progress': n})` pattern; confidence HIGH (core Celery feature, stable across 4.x / 5.x)
