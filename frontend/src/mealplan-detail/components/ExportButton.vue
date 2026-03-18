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
        <polyline points="10 9 9 9 8 9"></polyline>
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
  // Guard against re-entrant execution after clearInterval
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
