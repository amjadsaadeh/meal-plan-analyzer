---
phase: 03-docker-and-frontend
plan: 02
subsystem: frontend
tags: [vue, async, export, i18n, progress-bar]
dependency_graph:
  requires: [02-02]
  provides: [async-export-ui]
  affects: [mealplan-detail-vue-app]
tech_stack:
  added: []
  patterns: [vue-composition-api, inject-provide, setInterval-polling, onUnmounted-cleanup]
key_files:
  created:
    - frontend/src/mealplan-detail/components/ExportButton.vue
  modified:
    - frontend/src/mealplan-detail/components/PageHeader.vue
    - meals/static/meals/scss/mealplan_detail.scss
    - meals/views.py
    - meals/locale/de/LC_MESSAGES/django.po
    - meals/locale/de/LC_MESSAGES/django.mo
    - meals/locale/en/LC_MESSAGES/django.po
    - meals/locale/en/LC_MESSAGES/django.mo
decisions:
  - ExportButton uses inject(planId/csrfToken/i18n) from main.js app.provide — no prop drilling needed
  - onUnmounted clears pollTimer to prevent dangling setInterval on navigation
  - pdfUrl prop kept in PageHeader.vue defineProps to avoid unnecessary breaking churn
metrics:
  duration: ~2 min
  completed: 2026-03-18
  tasks_completed: 2
  files_changed: 7
---

# Phase 3 Plan 2: ExportButton Vue Component Summary

**One-liner:** Async PDF export button with setInterval polling, in-page progress bar, and automatic download on completion.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create ExportButton.vue and update PageHeader.vue | 6fc2230 | ExportButton.vue (new), PageHeader.vue, mealplan_detail.scss |
| 2 | Add i18n strings to views.py and both locale .po files | 75331b7 | views.py, django.po (de+en), django.mo (de+en) |

## What Was Built

### ExportButton.vue
A three-state Vue component (`idle` / `exporting` / `error`):

- **Idle:** Renders a `<button class="btn-pdf">` with PDF icon and `i18n.exportPdf` label
- **Exporting:** Shows a `<progress>` bar updating from 0–100% with percentage label; polls `/api/export-jobs/${jobId}/` every 1500ms via `setInterval`
- **Error:** Shows error message and Retry button; retry calls `startExport()` again

The `startExport()` function POSTs to `/api/export-jobs/` with `meal_plan_id`. When `pollJob()` detects `status === 'done'`, it assigns `window.location.href = /api/export-jobs/${jobId}/result/` to trigger the browser download. `onUnmounted` clears the timer to prevent memory/behavior leaks on navigation.

### PageHeader.vue
Replaced the `<a :href="previewUrl">` synchronous link with `<ExportButton />`. Import added. The `pdfUrl` and `previewUrl` prop definitions are retained (harmless, prevents churn).

### SCSS
Added `.export-progress`, `.export-progress-bar` (with webkit/moz vendor prefixes), `.export-progress-label`, `.export-error`, `.export-error-msg` at end of `mealplan_detail.scss`. Uses existing CSS custom properties (`--primary`, `--glass-border`, `--text-dim`, `--danger`).

### i18n
Added `"exportFailed"` and `"retry"` keys to the `i18n` dict in `meal_plan_detail` view. German: "Export fehlgeschlagen. Bitte erneut versuchen." / "Erneut versuchen". `.mo` files compiled.

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- `pdfUrl` prop left in `PageHeader.vue` `defineProps` — removing it would be unnecessary churn
- `inject('planId')` sourced from `main.js` `app.provide('planId', el.dataset.planId)` — already wired

## Self-Check

### Files Created
- [x] `frontend/src/mealplan-detail/components/ExportButton.vue` — FOUND

### Commits
- [x] 6fc2230 — FOUND
- [x] 75331b7 — FOUND

### Verification
- [x] `pnpm build` exits 0
- [x] PageHeader.vue has `import ExportButton` and `<ExportButton />`
- [x] `<a :href="previewUrl">` PDF link removed from PageHeader.vue
- [x] `.export-progress-bar` present in mealplan_detail.scss with vendor prefixes
- [x] `exportFailed` and `retry` keys in views.py i18n dict
- [x] German .po file has "Export fehlgeschlagen" and "Erneut versuchen"
- [x] Both .mo files updated (timestamp 2026-03-18)
- [x] `manage.py check` — 0 issues

## Self-Check: PASSED
