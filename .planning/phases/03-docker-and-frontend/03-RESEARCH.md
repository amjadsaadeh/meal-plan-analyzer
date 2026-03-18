# Phase 3: Docker and Frontend - Research

**Researched:** 2026-03-18
**Domain:** Docker Compose service topology + Vue 3 async export UI (polling, progress bar, file download trigger)
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-03 | Docker Compose runs a Redis service and a Celery worker service sharing the same image as the web container | Confirmed: existing `docker-compose.yml` has `web` and `db` services only; Redis and worker services must be added; same image reuse via `build: .` with different `command:` is the standard pattern |
| INFRA-04 | Web and worker containers share a media volume so the worker can write PDFs that the web container can serve | Confirmed: `MEDIA_ROOT = BASE_DIR / "media"` in settings; a named Docker volume mounted at `/app/media` in both web and worker is the correct solution; PDF files saved to `exports/` subdirectory by task |
| UI-01 | The PDF export link on `mealplan_detail` is replaced with an async export button component | Confirmed: current `PageHeader.vue` has `<a :href="previewUrl">` as the only export control; the `pdfUrl` provided via `main.js` inject points to sync `meal-plan-pdf` view; replacement requires a new `ExportButton.vue` component in `PageHeader.vue` |
| UI-02 | Clicking export triggers `POST /api/export-jobs/` and starts polling `GET /api/export-jobs/<id>/` at ~1.5s intervals | API endpoints confirmed built in Phase 2; polling via `setInterval` with 1500ms is the correct implementation (no SSE/WebSocket per project decision) |
| UI-03 | An in-page progress bar shows current `progress` percentage while the job is `pending` or `running` | Native `<progress>` element or CSS-animated `<div>` with `width: {n}%` — no external library needed; project uses vanilla CSS with SCSS variables |
| UI-04 | When `status=done`, the browser automatically triggers a file download and the progress bar clears | `window.location.href = '/api/export-jobs/{id}/result/'` triggers download when `FileResponse` has `as_attachment=True`; no anchor click simulation needed |
| UI-05 | When `status=failed`, an error message is displayed inline with an option to retry | Simple conditional render in the component; retry resets state and calls `POST /api/export-jobs/` again |
</phase_requirements>

---

## Summary

Phase 3 has two independent work areas: (1) Docker Compose infrastructure additions and (2) Vue frontend UI. Neither area blocks the other and they can be planned as separate tasks within the phase.

For Docker, the existing `docker-compose.yml` needs three additions: a `redis` service, a `worker` service (same image as `web`, different command), and a named `media_files` volume shared between `web` and `worker`. The `web` service must also add `CELERY_BROKER_URL`, `REDIS_URL`, and `SITE_BASE_URL` to its environment block, and both `web` and `worker` must declare the shared media volume mount. The Dockerfile does not need to change — the same image already installs WeasyPrint system dependencies and the Python venv.

For the frontend, the change is localized to `PageHeader.vue` (replace the `<a>` PDF link with an async button) and optionally extract the polling logic into a composable. The `pdfUrl` inject currently provided by `main.js` can be replaced with `exportJobsUrl` pointing to `/api/export-jobs/`. The `ExportButton` component manages three states: idle (button), in-progress (progress bar), and error (message + retry). When `status=done`, `window.location.href` is pointed at the result URL, which the browser downloads as an attachment. There is no need for a new Vue composable library — the project uses plain Vue 3 `<script setup>` with `ref`/`computed`/`inject`.

**Primary recommendation:** Two sequential plans: (1) Docker Compose infrastructure — add Redis/worker services and shared media volume, (2) Vue frontend — replace `PageHeader.vue` export link with `ExportButton.vue` polling component and add a Playwright test.

---

## Standard Stack

### Core (all already installed — no new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Docker Compose v2 | Bundled with Docker Desktop / Docker Engine | Multi-container orchestration | Already in use; project has `docker-compose.yml` |
| Vue 3 (Composition API) | Already installed via `frontend/` | Reactive UI components | Existing mealplan-detail app uses `<script setup>` pattern throughout |
| SCSS via `sass-processor` | Already installed | Styling the export button and progress bar | All detail page styles live in `mealplan_detail.scss` |
| Playwright | Already installed for frontend tests | Browser-level E2E verification | Frontend test suite uses `logged_in_page` fixture |

### Supporting (no new packages)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Native `fetch` API | Browser built-in | HTTP calls for POST job and GET poll | Already used in all other Vue components in this app |
| Native `<progress>` element or CSS `width` trick | Browser built-in | Progress bar rendering | No external library needed; project avoids heavyweight UI libs |
| `window.location.href` | Browser built-in | Trigger file download | Standard pattern for `Content-Disposition: attachment` responses |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `setInterval` polling at 1.5s | Server-Sent Events / WebSockets | SSE/WS is out of scope per requirements; polling sufficient for 5-30s export latency |
| `window.location.href` for download | Dynamic `<a>` element `.click()` | Both work identically for `as_attachment=True` FileResponse; `window.location.href` is simpler |
| Named Docker volume for media | Bind-mount `./media:/app/media` | Bind-mount requires the `./media/` directory to exist on the host before first run; named volume is created automatically by Docker |

**Installation:** No new packages. Phase 3 is configuration (Docker) + Vue component authoring only.

---

## Architecture Patterns

### Recommended File Changes for Phase 3

```
docker-compose.yml                          # MODIFY: add redis/worker services + media volume
meals/views.py                              # MODIFY: add export_jobs_url to mealplan_detail context
meals/templates/meals/mealplan_detail.html.j2  # MODIFY: add data-export-jobs-url attribute
frontend/src/mealplan-detail/main.js        # MODIFY: provide exportJobsUrl from dataset
frontend/src/mealplan-detail/components/
├── PageHeader.vue                          # MODIFY: replace <a> link with ExportButton
└── ExportButton.vue                        # NEW: polling export button component

tests/frontend/
└── test_export_button.py                   # NEW: Playwright test for export UI flow
```

### Pattern 1: Docker Compose Service Topology

**What:** Add `redis`, `worker` services and a `media_files` named volume to the existing compose file. Web and worker share the same built image; the worker runs Celery instead of gunicorn.

**When to use:** Always for multi-service Django + Celery deployments.

```yaml
# docker-compose.yml — additions (merge with existing services/volumes)

services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  worker:
    build: .
    command: >
      celery -A config worker
        --loglevel=info
        --concurrency=2
        --max-tasks-per-child=50
    volumes:
      - media_files:/app/media
    environment:
      - SECRET_KEY=${SECRET_KEY:-change-me-generate-a-real-key-for-production}
      - DEBUG=True
      - DATABASE_URL=postgres://mealplanner:mealplanner@db:5432/mealplanner
      - CELERY_BROKER_URL=redis://redis:6379/0
      - REDIS_URL=redis://redis:6379/1
      - SITE_BASE_URL=http://web:8000
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  web:
    # ... existing config ...
    volumes:
      - .:/app
      - media_files:/app/media    # ADD: shared media volume
    environment:
      # ... existing env ...
      - CELERY_BROKER_URL=redis://redis:6379/0   # ADD
      - REDIS_URL=redis://redis:6379/1            # ADD
      - SITE_BASE_URL=http://web:8000             # ADD
    depends_on:
      db:
        condition: service_healthy
      redis:                          # ADD
        condition: service_healthy

volumes:
  postgres_data:
  media_files:    # ADD: named volume for PDF storage
```

**Critical details:**
- `SITE_BASE_URL=http://web:8000` uses the Docker internal service name `web`, not `localhost`. The Celery worker needs to resolve the web container for WeasyPrint's URL fetcher to load static assets over HTTP when needed. However, `django_url_fetcher` in the project resolves static/media files to local disk paths using `finders.find()`, so this URL is mostly used as the `base_url` parameter for WeasyPrint HTML parsing — it does NOT require a live HTTP connection to the web container.
- The `media_files` volume must appear in BOTH `web` and `worker` volumes sections and must be declared in the top-level `volumes:` block.
- The `worker` service does NOT need to mount `.:app` (the full source bind-mount). The Dockerfile already bakes in all application code. Only the `media_files` volume is needed.
- `--max-tasks-per-child=50` on the CLI is redundant with `CELERY_WORKER_MAX_TASKS_PER_CHILD=50` in settings.py (set in Phase 1), but makes the intent explicit in the compose file.

### Pattern 2: ExportButton Vue Component State Machine

**What:** A self-contained component with three rendering states: `idle`, `exporting` (shows progress bar), and `error` (shows message + retry button). State transitions are driven by the polling loop.

**When to use:** This is the only correct design for UI-01 through UI-05.

```javascript
// ExportButton.vue — state machine

// States:
// idle       → user sees "Export PDF" button
// exporting  → user sees progress bar (0-100%) + cancel is not implemented
// error      → user sees error message + "Retry" button

const state = ref('idle')       // 'idle' | 'exporting' | 'error'
const progress = ref(0)
const errorMessage = ref('')
let pollTimer = null
let jobId = null

async function startExport() {
  state.value = 'exporting'
  progress.value = 0
  errorMessage.value = ''

  const res = await fetch('/api/export-jobs/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ meal_plan_id: parseInt(planId) }),
  })

  if (!res.ok) {
    state.value = 'error'
    errorMessage.value = i18n.exportError || 'Export failed. Please retry.'
    return
  }

  const job = await res.json()
  jobId = job.id
  pollTimer = setInterval(pollJob, 1500)
}

async function pollJob() {
  try {
    const res = await fetch(`/api/export-jobs/${jobId}/`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const job = await res.json()
    progress.value = job.progress

    if (job.status === 'done') {
      clearInterval(pollTimer)
      pollTimer = null
      state.value = 'idle'
      progress.value = 0
      // Trigger browser download
      window.location.href = `/api/export-jobs/${jobId}/result/`
    } else if (job.status === 'failed') {
      clearInterval(pollTimer)
      pollTimer = null
      state.value = 'error'
      errorMessage.value = job.error_message || i18n.exportFailed || 'Export failed. Please retry.'
    }
    // 'pending' and 'running' → keep polling
  } catch (e) {
    clearInterval(pollTimer)
    pollTimer = null
    state.value = 'error'
    errorMessage.value = i18n.networkError || 'Network error. Please retry.'
  }
}

function retry() {
  jobId = null
  startExport()
}

// Cleanup on unmount
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
```

### Pattern 3: Progress Bar HTML + CSS

**What:** Inline `<progress>` element using the native HTML element. CSS is minimal and consistent with the existing SCSS token system.

**When to use:** Always for this component. The native `<progress>` element has built-in accessibility semantics (`role="progressbar"`), no dependencies, and works across all modern browsers.

```html
<!-- ExportButton.vue template fragment -->
<template>
  <div class="export-btn-wrapper">
    <!-- idle state -->
    <button
      v-if="state === 'idle'"
      class="btn-pdf"
      @click="startExport"
    >
      <svg><!-- PDF icon --></svg>
      {{ i18n.exportPdf }}
    </button>

    <!-- exporting state -->
    <div v-else-if="state === 'exporting'" class="export-progress">
      <progress
        class="export-progress-bar"
        :value="progress"
        max="100"
      ></progress>
      <span class="export-progress-label">{{ progress }}%</span>
    </div>

    <!-- error state -->
    <div v-else-if="state === 'error'" class="export-error">
      <span class="export-error-msg">{{ errorMessage }}</span>
      <button class="btn-pdf" @click="retry">{{ i18n.retry }}</button>
    </div>
  </div>
</template>
```

```scss
// Add to mealplan_detail.scss

.export-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.export-progress-bar {
  width: 120px;
  height: 8px;
  appearance: none;
  border-radius: 4px;
  overflow: hidden;

  &::-webkit-progress-bar {
    background: var(--glass-border);
    border-radius: 4px;
  }

  &::-webkit-progress-value {
    background: var(--primary);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  &::-moz-progress-bar {
    background: var(--primary);
    border-radius: 4px;
  }
}

.export-progress-label {
  font-size: 0.75rem;
  color: var(--text-dim);
  min-width: 32px;
}

.export-error {
  display: flex;
  align-items: center;
  gap: 8px;
}

.export-error-msg {
  font-size: 0.75rem;
  color: var(--danger);
  max-width: 200px;
}
```

### Pattern 4: Wiring ExportButton into PageHeader.vue

**What:** Replace the existing `<a :href="previewUrl">` export link in `PageHeader.vue` with the new `ExportButton` component. The `pdfUrl` prop is no longer needed; `exportJobsUrl` replaces it.

**Current `PageHeader.vue` (lines 29-39):**
```html
<div style="display: flex; gap: 8px;">
  <a :href="previewUrl" target="_blank" class="btn-pdf">
    <!-- PDF icon SVG -->
    {{ i18n.exportPdf }}
  </a>
</div>
```

**After change:**
```html
<div style="display: flex; gap: 8px;">
  <ExportButton />
</div>
```

`ExportButton` injects `csrfToken`, `planId`, and `i18n` from the app-level provides already set up in `main.js`. It does NOT need new props passed from `PageHeader` because all required data is already provided at the app root.

**Note on `pdfUrl`:** The `pdfUrl` is currently provided in `main.js` via `app.provide('pdfUrl', el.dataset.pdfUrl)`. After Phase 3, `pdfUrl` is no longer used by any component. The `data-pdf-url` attribute in the template and the `pdf_url` context variable in the view can be removed, or left in place as harmless dead code. Removing them is cleaner.

### Pattern 5: Django View Context Change

**What:** The `meal_plan_detail` view currently passes `pdf_url` to the template. After Phase 3, the frontend no longer needs this — the export job URL is always `/api/export-jobs/` (a fixed string, not plan-specific). The export jobs API URL can be hardcoded in the Vue component or passed via the template.

**Recommendation:** Hardcode `/api/export-jobs/` in `ExportButton.vue`. The plan ID is already available via `inject('planId')`. This avoids a template/view change entirely.

If the team prefers template-driven URLs (for consistency with how `previewUrl` and `planListUrl` are passed): add `data-export-jobs-url="/api/export-jobs/"` to the template element and `app.provide('exportJobsUrl', el.dataset.exportJobsUrl)` in `main.js`. Either approach works.

### Pattern 6: Playwright Test for Export Flow

**What:** E2E test that verifies the UI flow using the `logged_in_page` fixture. The test mocks or patches the Celery task to avoid needing a real worker in CI.

**The challenge:** The export button kicks off a real Celery task. In Playwright tests, there is no Celery worker running. Three options:

1. **Mock the API responses** using Playwright's `page.route()` to intercept `/api/export-jobs/` POST and poll responses — this is the cleanest option and tests the UI logic without backend complexity.

2. **Patch the task at the Django level** — override `generate_pdf_task` to execute synchronously and return immediately. Complex to set up in Playwright tests.

3. **Skip the integration test** and rely on the existing API tests (Phase 2) + task unit tests (Phase 2) for backend coverage; write only a basic UI smoke test (button is present, is clickable).

**Recommendation:** Use Playwright's `page.route()` to mock the API. This tests the full UI state machine (idle → exporting → done → download triggered) without needing a worker. This pattern is standard in Playwright testing.

```python
# tests/frontend/test_export_button.py

@pytest.mark.django_db(transaction=True)
def test_export_button_present(logged_in_page, live_server, meal_plan_with_day):
    """Export button renders on the meal plan detail page."""
    plan, _ = meal_plan_with_day
    page = logged_in_page
    page.goto(f"{live_server.url}/meal-plan/{plan.pk}/")
    # The export button should exist
    export_btn = page.locator('button.btn-pdf')
    expect(export_btn).to_be_visible()

@pytest.mark.django_db(transaction=True)
def test_export_button_shows_progress(logged_in_page, live_server, meal_plan_with_day):
    """Clicking export transitions to progress bar state."""
    plan, _ = meal_plan_with_day
    page = logged_in_page
    fake_job_id = "12345678-1234-1234-1234-123456789abc"

    # Mock POST /api/export-jobs/ to return a pending job
    page.route("**/api/export-jobs/", lambda route: route.fulfill(
        status=201,
        content_type="application/json",
        body=f'{{"id": "{fake_job_id}", "status": "pending", "progress": 0, "error_message": ""}}'
    ))
    # Mock GET poll to return running at 50%
    page.route(f"**/api/export-jobs/{fake_job_id}/", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'{{"id": "{fake_job_id}", "status": "running", "progress": 50, "error_message": ""}}'
    ))

    page.goto(f"{live_server.url}/meal-plan/{plan.pk}/")
    page.locator('button.btn-pdf').click()
    # Progress bar should appear
    expect(page.locator('.export-progress-bar')).to_be_visible()
```

### Anti-Patterns to Avoid

- **Don't use `depends_on: redis` without a healthcheck condition:** `depends_on: redis` with just the service name waits for the container to start, not for Redis to be ready to accept connections. Use `condition: service_healthy` with Redis's `redis-cli ping` healthcheck.
- **Don't mount `./media:/app/media` as a bind-mount in compose:** The `./media/` directory may not exist before first run, causing a Docker error. Use a named volume instead — Docker creates named volumes automatically.
- **Don't put CFFI/WeasyPrint-heavy tasks in the web process:** The web container should NOT run Celery tasks — it runs gunicorn. The worker container runs Celery. They share code via the same image, not by running both processes in one container.
- **Don't call `clearInterval` with `pollTimer` before checking if it was set:** Always `clearInterval(pollTimer); pollTimer = null` in both the `done` and `failed` branches AND in `onUnmounted` to prevent memory leaks from abandoned intervals.
- **Don't redirect to the result URL before `status === 'done'`:** The `FileResponse` returns 404 if not done. Always check `status === 'done'` before triggering `window.location.href`.
- **Don't leave the export button in a disabled/stuck state:** If the network fails entirely during polling (not just an error status), the component must transition to the `error` state and show the retry option. The `try/catch` in `pollJob` is mandatory.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bar UI widget | Custom SVG/canvas animation | Native `<progress>` element with CSS | Browser-native, accessible, no dependency, matches project style |
| File download trigger | `<a download>` element creation + click simulation | `window.location.href = resultUrl` | Identical result; simpler code; works for cross-origin same-site cookies |
| Celery task concurrency limit | Custom semaphore or job queue | `--concurrency=2` flag on `celery worker` command | Celery's prefork pool already handles this |
| Redis connection retry | Custom `asyncio` reconnect loop | Redis `7-alpine` with `redis-cli ping` healthcheck + compose `condition: service_healthy` | Docker compose retries service startup until healthcheck passes |
| Polling abort on unmount | `AbortController` / complex lifecycle | `clearInterval(pollTimer)` in `onUnmounted()` | Simple and correct for `setInterval`-based polling |

---

## Common Pitfalls

### Pitfall 1: SITE_BASE_URL Uses `localhost` Instead of Docker Service Name

**What goes wrong:** Worker container tries to resolve `http://localhost:8000` for WeasyPrint's `base_url`. Inside Docker, `localhost` refers to the worker container itself, not the web container. This may or may not matter depending on whether WeasyPrint ever makes HTTP requests (it does for CSS `@import` and image `<src>` if the URL is not intercepted by `django_url_fetcher`).

**Why it happens:** The `.env.example` default is `SITE_BASE_URL=http://localhost:8000`, which is correct for local dev but wrong for Docker networking.

**How to avoid:** Set `SITE_BASE_URL=http://web:8000` in the `worker` service environment in `docker-compose.yml`. The `web` service name resolves within Docker's internal network. This is a Docker Compose only change — local dev still reads `SITE_BASE_URL` from `.env` which defaults to `localhost`.

**Warning signs:** WeasyPrint logs "Failed to load" for CSS/image URLs during task execution in the worker container.

### Pitfall 2: Media Volume Not Mounted on Both Services

**What goes wrong:** Worker writes the PDF to `/app/media/exports/filename.pdf` inside the worker container. The web container does not see this file because they have separate filesystem namespaces.

**Why it happens:** Named volumes must be declared in BOTH services' `volumes:` section and the top-level `volumes:` block. Forgetting either the web mount or the top-level declaration silently fails (Docker creates an anonymous volume for the worker only).

**How to avoid:** Verify by listing `volumes:` section under each service and the top-level `volumes:` block. After `docker compose up`, run `docker compose exec web ls /app/media/exports/` to confirm files written by the worker are visible.

**Warning signs:** `GET /api/export-jobs/<id>/result/` returns a 500 error (FileField path exists in DB but file is not found on disk) after the job completes.

### Pitfall 3: `pollTimer` Left Running After Component Unmount

**What goes wrong:** If the user navigates away from the detail page while a job is in progress, the `setInterval` callback continues firing. The next call attempts to fetch `/api/export-jobs/<id>/` and may update state on an unmounted component, causing Vue warnings.

**Why it happens:** `setInterval` persists beyond Vue component lifecycle unless explicitly cleared.

**How to avoid:** Always call `clearInterval(pollTimer); pollTimer = null` inside `onUnmounted()`. Additionally, `pollTimer = null` after clearing prevents double-clear on subsequent unmounts.

**Warning signs:** Vue DevTools shows "Component is unmounted" warnings in the browser console during navigation.

### Pitfall 4: `<progress>` Styling Requires Vendor Prefixes

**What goes wrong:** The default `<progress>` element appearance varies across browsers. Without explicit vendor-prefixed CSS pseudo-elements, the progress bar may show the OS default styling (ugly, inconsistent).

**Why it happens:** `<progress>` styling uses non-standard but widely-supported pseudo-elements: `::-webkit-progress-bar`, `::-webkit-progress-value`, `::-moz-progress-bar`.

**How to avoid:** Set `appearance: none` (with `-webkit-appearance: none` for older WebKit) and style all three vendor pseudo-elements. Tested: this works in Chromium (Playwright CI) and Firefox. See SCSS example in Code Examples.

**Warning signs:** Progress bar shows native grey bar instead of the project's `--primary` teal color.

### Pitfall 5: Polling Continues After Component Receives `done` Status

**What goes wrong:** If `clearInterval(pollTimer)` is called correctly but `window.location.href` assignment happens on the same tick, the redirect may race with a final poll response.

**Why it happens:** `setInterval` callbacks can queue up if the previous callback was still executing (e.g., a slow fetch). Clearing the interval before processing the response prevents this.

**How to avoid:** At the top of `pollJob()`, check `if (!pollTimer) return` to guard against re-entrant execution after clearInterval is called. Alternatively, always clear the interval as the FIRST thing in the `done` and `failed` branches.

**Warning signs:** Console shows duplicate fetch requests to `/api/export-jobs/<id>/` after download starts.

### Pitfall 6: Worker Service Mounts Full Source as Bind-Mount

**What goes wrong:** Adding `- .:/app` to the worker service volumes (copying the web service's volume config) means the worker uses the host filesystem. This is unnecessary (the image already has the code baked in) and can cause confusion — changes to host files affect the worker but not the built image.

**Why it happens:** Copy-paste from the `web` service config.

**How to avoid:** The `worker` service should NOT mount `- .:/app`. Only mount `- media_files:/app/media`. The Dockerfile bakes in all application code. The `web` service mounts `- .:/app` only for live-reload during development — the worker does not need live-reload.

---

## Code Examples

### Complete docker-compose.yml additions (production-ready)

```yaml
# Source: Docker Compose v2 documentation + project conventions
services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  worker:
    build: .
    command: >
      celery -A config worker
        --loglevel=info
        --concurrency=2
        --max-tasks-per-child=50
    volumes:
      - media_files:/app/media
    environment:
      - SECRET_KEY=${SECRET_KEY:-change-me-generate-a-real-key-for-production}
      - DEBUG=True
      - DATABASE_URL=postgres://mealplanner:mealplanner@db:5432/mealplanner
      - CELERY_BROKER_URL=redis://redis:6379/0
      - REDIS_URL=redis://redis:6379/1
      - SITE_BASE_URL=http://web:8000
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
  media_files:
```

Additions to the existing `web` service:
```yaml
  web:
    # ... existing config unchanged ...
    volumes:
      - .:/app
      - media_files:/app/media    # ADD THIS
    environment:
      # ... existing env vars unchanged ...
      - CELERY_BROKER_URL=redis://redis:6379/0   # ADD
      - REDIS_URL=redis://redis:6379/1            # ADD
      - SITE_BASE_URL=http://web:8000             # ADD
    depends_on:
      db:
        condition: service_healthy
      redis:                          # ADD
        condition: service_healthy
```

### ExportButton.vue (complete component)

```vue
<!-- frontend/src/mealplan-detail/components/ExportButton.vue -->
<template>
  <div class="export-btn-wrapper">
    <button
      v-if="state === 'idle'"
      class="btn-pdf"
      @click="startExport"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
      </svg>
      {{ i18n.exportPdf }}
    </button>

    <div v-else-if="state === 'exporting'" class="export-progress">
      <progress class="export-progress-bar" :value="progress" max="100"></progress>
      <span class="export-progress-label">{{ progress }}%</span>
    </div>

    <div v-else-if="state === 'error'" class="export-error">
      <span class="export-error-msg">{{ errorMessage }}</span>
      <button class="btn-pdf" @click="retry">{{ i18n.retry || 'Retry' }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onUnmounted } from 'vue'

const i18n = inject('i18n')
const csrfToken = inject('csrfToken')
const planId = inject('planId')

const state = ref('idle')      // 'idle' | 'exporting' | 'error'
const progress = ref(0)
const errorMessage = ref('')
let pollTimer = null
let jobId = null

async function startExport() {
  state.value = 'exporting'
  progress.value = 0
  errorMessage.value = ''
  jobId = null

  try {
    const res = await fetch('/api/export-jobs/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ meal_plan_id: parseInt(planId) }),
    })

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    const job = await res.json()
    jobId = job.id
    progress.value = job.progress || 0
    pollTimer = setInterval(pollJob, 1500)
  } catch (e) {
    state.value = 'error'
    errorMessage.value = i18n.networkError || 'Export failed. Please retry.'
  }
}

async function pollJob() {
  // Guard: if cleared already (e.g. concurrent callbacks), bail out
  if (!pollTimer) return

  try {
    const res = await fetch(`/api/export-jobs/${jobId}/`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const job = await res.json()
    progress.value = job.progress

    if (job.status === 'done') {
      clearInterval(pollTimer)
      pollTimer = null
      state.value = 'idle'
      progress.value = 0
      window.location.href = `/api/export-jobs/${jobId}/result/`
    } else if (job.status === 'failed') {
      clearInterval(pollTimer)
      pollTimer = null
      state.value = 'error'
      errorMessage.value = job.error_message || i18n.exportFailed || 'Export failed. Please retry.'
    }
    // 'pending' | 'running' → keep polling
  } catch (e) {
    clearInterval(pollTimer)
    pollTimer = null
    state.value = 'error'
    errorMessage.value = i18n.networkError || 'Network error. Please retry.'
  }
}

function retry() {
  jobId = null
  startExport()
}

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>
```

### i18n keys needed

The `ExportButton` component uses `i18n.exportPdf`, `i18n.networkError`, `i18n.exportFailed`, and `i18n.retry`. The first two already exist in the i18n dict passed from the Django view. `exportFailed` and `retry` must be added.

Check current i18n keys in `meals/views.py` around line 200-244 (the `i18n` dict assembled before `render()`). Add:
```python
"exportFailed": _("Export failed. Please retry."),
"retry": _("Retry"),
```

Add translations to `meals/locale/de/LC_MESSAGES/django.po` as well.

### Playwright test fixture for mocked export API

```python
# tests/frontend/test_export_button.py
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.django_db(transaction=True)
def test_export_button_visible(logged_in_page, live_server, meal_plan_with_day):
    """Export button renders on the meal plan detail page."""
    plan, _ = meal_plan_with_day
    page = logged_in_page
    page.goto(f"{live_server.url}/meal-plan/{plan.pk}/")
    page.wait_for_selector('.container')
    # Vue may need a moment to mount
    export_btn = page.locator('button.btn-pdf')
    expect(export_btn).to_be_visible(timeout=5000)


@pytest.mark.django_db(transaction=True)
def test_export_progress_shown_then_error(logged_in_page, live_server, meal_plan_with_day):
    """Export button transitions to progress bar on click, then to error on failure."""
    plan, _ = meal_plan_with_day
    page = logged_in_page
    fake_job_id = "12345678-0000-0000-0000-000000000001"

    # Mock POST: return pending job
    page.route("**/api/export-jobs/", lambda route: route.fulfill(
        status=201,
        content_type="application/json",
        body=f'{{"id": "{fake_job_id}", "status": "pending", "progress": 0, "error_message": ""}}'
    ) if route.request.method == "POST" else route.continue_())

    # Mock GET poll: return failed status
    page.route(f"**/api/export-jobs/{fake_job_id}/", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'{{"id": "{fake_job_id}", "status": "failed", "progress": 0, "error_message": "Test failure"}}'
    ))

    page.goto(f"{live_server.url}/meal-plan/{plan.pk}/")
    page.wait_for_selector('button.btn-pdf', timeout=5000)
    page.locator('button.btn-pdf').click()

    # Progress bar should appear briefly, then error state
    expect(page.locator('.export-error')).to_be_visible(timeout=5000)
    expect(page.locator('.export-error-msg')).to_contain_text('Test failure')
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync PDF link (`/meal-plan/<pk>/pdf/`) | Async export button with polling | Phase 3 | PDF generation no longer blocks the HTTP request; web process stays responsive |
| `<a href="...">` for PDF download | `window.location.href = resultUrl` | Phase 3 | Same browser download behavior, but triggered after async job completion |
| Single-service Docker Compose (web + db) | Three-service (web + db + redis + worker) | Phase 3 | Celery tasks execute in isolated worker process; web process never touched by WeasyPrint CFFI |

**Deprecated after Phase 3:**
- `pdfUrl` / `data-pdf-url` in `mealplan_detail.html.j2` template and `meal_plan_detail` view context — no longer needed; can be removed
- Direct link to `meal-plan-pdf` view from the detail page — superseded by async export

---

## Open Questions

1. **Should `meal-plan-pdf` view be kept or removed?**
   - What we know: The sync PDF view (`/meal-plan/<pk>/pdf/`) still exists and is used by the preview feature (`meal-plan-preview`). The `mealplan_preview.html.j2` template and `meal_plan_preview` view embed the PDF content.
   - What's unclear: Does `meal_plan_preview_content` use the sync view? Check `views.py` around `meal_plan_preview_content`.
   - Recommendation: Keep the sync view in place. Only replace the export button in the detail page. The preview feature continues to use the sync rendering path.

2. **Worker service: should `DEBUG=True` in compose?**
   - What we know: The `web` service already has `DEBUG=True` in `docker-compose.yml`. The worker should use the same settings for consistency in local dev.
   - What's unclear: Whether any Celery behavior changes between `DEBUG=True` and `DEBUG=False` in the worker.
   - Recommendation: Set `DEBUG=True` in the worker service for local compose (same as web). In production (Kubernetes), both run with `DEBUG=False` via Ansible vault — no change needed.

3. **`data-export-jobs-url` attribute: hardcode or template-driven?**
   - What we know: All other API URLs (threshold presets, foods) are hardcoded strings in the Vue components.
   - What's unclear: Whether the project convention prefers template-driven URLs everywhere.
   - Recommendation: Hardcode `/api/export-jobs/` in `ExportButton.vue`. This is consistent with how `Toolbar.vue` hardcodes `/api/threshold-presets/` and `MealPlanDetailApp.vue` hardcodes `/api/mealplan-days/`, `/api/mealplan-foods/`, etc.

---

## Sources

### Primary (HIGH confidence)

- `docker-compose.yml` — confirmed current state: `web` and `db` services only; no Redis, no worker, no media volume
- `Dockerfile` — confirmed multi-stage build with WeasyPrint system deps; same image suitable for both web and worker
- `config/settings.py:157-158` — confirmed `MEDIA_ROOT = BASE_DIR / "media"` and `MEDIA_URL = "/media/"`
- `config/settings.py:217-245` — confirmed all Celery settings set in Phase 1; `CELERY_BROKER_URL`, `REDIS_URL`, `SITE_BASE_URL` env vars already in `.env.example`
- `frontend/src/mealplan-detail/components/PageHeader.vue` — confirmed existing `<a :href="previewUrl">` export link is the only export control; `pdfUrl` prop currently unused (previewUrl is used for the link text "Export PDF")
- `frontend/src/mealplan-detail/main.js` — confirmed `pdfUrl` provided from `el.dataset.pdfUrl`; `planId`, `csrfToken`, `i18n` all provided from root — `ExportButton` can inject these without new props
- `meals/views.py:254` — confirmed `pdf_url: reverse("meal-plan-pdf", ...)` in context; i18n dict confirmed at lines ~200-244
- `tests/frontend/conftest.py` — confirmed `logged_in_page` fixture pattern; `meal_plan_with_day` fixture available
- Phase 2 summaries — confirmed `ExportJobViewSet` API is complete and tested; all three endpoints working

### Secondary (MEDIUM confidence)

- Docker Compose v2 healthcheck syntax — verified from Docker documentation pattern; `redis-cli ping` is the standard Redis healthcheck
- Playwright `page.route()` for API mocking — verified from Playwright docs as the standard interception pattern
- Native `<progress>` vendor prefixes — verified from MDN Web Docs; `::-webkit-progress-value` and `::-moz-progress-bar` confirmed

### Tertiary (LOW confidence — flag for validation)

- `window.location.href` triggering download for `Content-Disposition: attachment` responses — consistent with training knowledge and standard browser behavior, but browser behavior can vary by security policy. LOW confidence. Verify by manual test in Chromium during Phase 3 execution.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all libraries confirmed from existing project inspection
- Architecture: HIGH — Docker topology derived from existing compose file; Vue patterns derived from existing component inspection; file locations confirmed
- Pitfalls: HIGH — all pitfalls derived from direct code/config inspection (missing volume mount, SITE_BASE_URL localhost vs service name, pollTimer cleanup, progress element styling)

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (Docker Compose v2 stable; Vue 3 Composition API stable; 30-day window)
