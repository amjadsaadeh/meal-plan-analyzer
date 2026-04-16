<template>
  <div>
    <div class="top-actions">
      <button class="btn-create" @click="createPreset" :disabled="creating">
        <svg
          width="20" height="20" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round"
          stroke-linejoin="round" style="margin-right: 8px;"
        >
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        {{ i18n.createPreset }}
      </button>
      <div class="search-wrapper">
        <PresetSearchBar v-model="searchQuery" :placeholder="i18n.searchPlaceholder" />
      </div>
    </div>

    <div class="table-card" :class="{ 'is-loading': loading }">
      <PresetTable
        :presets="presets"
        :loading="loading"
        :search-query="searchQuery"
      />
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, inject } from 'vue'
import PresetSearchBar from './PresetSearchBar.vue'
import PresetTable from './PresetTable.vue'
import type { ThresholdPreset, PaginatedResponse, I18n } from '../../types/index'

const csrfToken = inject<string>('csrfToken')!
const i18n = inject<I18n>('i18n')!
const presetEditorBaseUrl = inject<string>('presetEditorBaseUrl')!

const presets = ref<ThresholdPreset[]>([])
const loading = ref(true)
const searchQuery = ref('')
const creating = ref(false)
const errorMsg = ref('')

async function fetchAll() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch('/api/threshold-presets/')
    if (!res.ok) throw new Error(String(res.status))
    const data: PaginatedResponse<ThresholdPreset> | ThresholdPreset[] = await res.json()
    presets.value = Array.isArray(data) ? data : (data.results ?? [])
  } catch (e) {
    errorMsg.value = i18n.networkError ?? 'Network error'
  } finally {
    loading.value = false
  }
}

async function doSearch(query: string) {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch(
      `/api/threshold-presets/?search=${encodeURIComponent(query)}`
    )
    if (!res.ok) throw new Error(String(res.status))
    const data: PaginatedResponse<ThresholdPreset> | ThresholdPreset[] = await res.json()
    presets.value = Array.isArray(data) ? data : (data.results ?? [])
  } catch (e) {
    errorMsg.value = i18n.networkError ?? 'Network error'
  } finally {
    loading.value = false
  }
}

async function createPreset() {
  creating.value = true
  errorMsg.value = ''
  try {
    const res = await fetch('/api/threshold-presets/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ name: i18n.newPresetName }),
    })
    if (!res.ok) throw new Error(String(res.status))
    const preset: ThresholdPreset = await res.json()
    window.location.href = presetEditorBaseUrl + preset.id + '/'
  } catch (e) {
    errorMsg.value = i18n.errorCreate ?? 'Error creating preset'
  } finally {
    creating.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, (q) => {
  clearTimeout(searchTimer ?? undefined)
  if (q.length >= 2) {
    searchTimer = setTimeout(() => doSearch(q), 0)
  } else if (q.length === 0) {
    fetchAll()
  }
})

onMounted(() => {
  fetchAll()
})
</script>
