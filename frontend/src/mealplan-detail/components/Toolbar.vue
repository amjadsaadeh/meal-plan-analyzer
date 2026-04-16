<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <button class="col-select-btn" @click="$emit('add-day')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        {{ i18n.addDay }}
      </button>
      <button id="colSelectBtn" class="col-select-btn" ref="colBtnRef" @click.stop="$emit('open-col-dropdown', $event.currentTarget as Element)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7"></rect>
          <rect x="14" y="3" width="7" height="7"></rect>
          <rect x="14" y="14" width="7" height="7"></rect>
          <rect x="3" y="14" width="7" height="7"></rect>
        </svg>
        {{ i18n.selectColumns }}
      </button>
    </div>
    <div class="toolbar-right">
      <div class="preset-search-container">
        <label class="preset-label" for="presetSearch">{{ i18n.referenceValueTemplate }}</label>
        <div class="preset-input-wrapper">
          <input
            type="text"
            id="presetSearch"
            class="preset-search-input"
            :placeholder="i18n.searchTemplate"
            autocomplete="off"
            v-model="presetQuery"
            @input="onPresetInput"
            @focus="onPresetInput"
            @click="onPresetInput"
            @blur="scheduleHidePresets"
          >
          <div class="preset-dropdown" :class="{ active: presetDropdownVisible }">
            <div
              v-for="p in presetResults"
              :key="p.id"
              class="preset-item"
              @mousedown.prevent="selectPreset(p)"
              v-html="highlightMatch(p.name, presetQuery)"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, inject } from 'vue'
import type { I18n, Nutrient, ThresholdPreset, PaginatedResponse } from '../../types/index'

const i18n = inject<I18n>('i18n')!

withDefaults(defineProps<{
  nutrients?: Nutrient[]
  visibleNutrients?: string[]
}>(), {
  nutrients: () => [],
  visibleNutrients: () => [],
})

const emit = defineEmits<{
  'add-day': []
  'open-col-dropdown': [btn: Element]
  'apply-preset': [preset: ThresholdPreset]
}>()

const presetQuery = ref('')
const presetResults = ref<ThresholdPreset[]>([])
const presetDropdownVisible = ref(false)
let presetTimer: ReturnType<typeof setTimeout> | null = null

function onPresetInput() {
  const q = presetQuery.value.trim()
  clearTimeout(presetTimer ?? undefined)
  const delay = q.length === 0 ? 0 : 300
  presetTimer = setTimeout(() => fetchPresets(q), delay)
}

async function fetchPresets(query: string) {
  try {
    const url = query
      ? `/api/threshold-presets/?search=${encodeURIComponent(query)}`
      : '/api/threshold-presets/'
    const res = await fetch(url)
    const data: PaginatedResponse<ThresholdPreset> | ThresholdPreset[] = await res.json()
    presetResults.value = Array.isArray(data) ? data : (data.results ?? [])
    presetDropdownVisible.value = presetResults.value.length > 0
  } catch (e) {
    console.error(e)
  }
}

function scheduleHidePresets() {
  setTimeout(() => { presetDropdownVisible.value = false }, 150)
}

function selectPreset(p: ThresholdPreset) {
  emit('apply-preset', p)
  presetQuery.value = ''
  presetDropdownVisible.value = false
}

function highlightMatch(text: string, query: string): string {
  if (!query) return text
  const semanticKeywords = ['low', 'high', 'energy', 'cal', 'kcal', 'kj']
  const tokens = query.toLowerCase().split(/\s+/)
    .filter(t => t.length >= 2 && !semanticKeywords.includes(t))
  if (tokens.length === 0) return text
  const pattern = tokens.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')
  return text.replace(regex, '<strong>$1</strong>')
}
</script>
