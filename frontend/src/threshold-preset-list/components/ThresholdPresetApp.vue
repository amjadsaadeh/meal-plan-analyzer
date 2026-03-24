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

<script setup>
import { ref, watch, onMounted, inject } from 'vue'
import PresetSearchBar from './PresetSearchBar.vue'
import PresetTable from './PresetTable.vue'

const csrfToken = inject('csrfToken')
const i18n = inject('i18n')
const presetEditorBaseUrl = inject('presetEditorBaseUrl')

const presets = ref([])
const loading = ref(true)
const searchQuery = ref('')
const creating = ref(false)
const errorMsg = ref('')

async function fetchAll() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch('/api/threshold-presets/')
    if (!res.ok) throw new Error(res.status)
    const data = await res.json()
    presets.value = data.results ?? (Array.isArray(data) ? data : [])
  } catch (e) {
    errorMsg.value = i18n.networkError ?? 'Network error'
  } finally {
    loading.value = false
  }
}

async function doSearch(query) {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch(
      `/api/threshold-presets/?search=${encodeURIComponent(query)}`
    )
    if (!res.ok) throw new Error(res.status)
    const data = await res.json()
    presets.value = data.results ?? (Array.isArray(data) ? data : [])
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
    if (!res.ok) throw new Error(res.status)
    const preset = await res.json()
    window.location.href = presetEditorBaseUrl + preset.id + '/'
  } catch (e) {
    errorMsg.value = i18n.errorCreate ?? 'Error creating preset'
  } finally {
    creating.value = false
  }
}

let searchTimer = null
watch(searchQuery, (q) => {
  clearTimeout(searchTimer)
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
