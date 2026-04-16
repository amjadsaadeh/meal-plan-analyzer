<template>
  <tr class="preset-row" @click="navigate">
    <td class="preset-name-cell">
      <span v-html="highlightMatch(preset.name, searchQuery)"></span>
    </td>
    <td
      v-for="key in DEFAULT_KEYS"
      :key="key"
      class="preset-nutrient-cell"
    >
      {{ formatThreshold(preset[key + '_min'], preset[key + '_max']) }}
    </td>
    <td class="col-actions" @click.stop>
      <button class="btn-icon-link" @click="navigate" title="Edit">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
      </button>
      <button class="btn-expand-chevron" @click="expanded = !expanded">
        <svg
          width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          :style="{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </td>
  </tr>
  <tr class="preset-expanded-row">
    <td :colspan="DEFAULT_KEYS.length + 2" style="padding: 0; border-bottom: 1px solid var(--glass-border);">
      <div class="expanded-content" :class="{ open: expanded }">
        <div class="preset-expanded-inner expanded-inner">
          <div
            v-for="nutrient in extendedNutrients"
            :key="nutrient.key"
            class="expanded-nutrient-item"
          >
            <span class="expanded-nutrient-label">{{ nutrient.label }} ({{ nutrient.unit }})</span>
            <span class="expanded-nutrient-val">
              {{ formatThreshold(preset[nutrient.key + '_min'], preset[nutrient.key + '_max']) }}
            </span>
          </div>
        </div>
      </div>
    </td>
  </tr>
</template>

<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import type { ThresholdPreset, Nutrient } from '../../types/index'

const props = withDefaults(defineProps<{
  preset: ThresholdPreset
  searchQuery?: string
}>(), {
  searchQuery: '',
})

const nutrients = inject<Nutrient[]>('nutrients')!
const presetEditorBaseUrl = inject<string>('presetEditorBaseUrl')!

const DEFAULT_KEYS = ['energy_in_kcal', 'water_in_g', 'carbohydrate_in_g', 'fat_in_g', 'protein_in_g']

const expanded = ref(false)

const extendedNutrients = computed(() =>
  nutrients.filter((n) => !DEFAULT_KEYS.includes(n.key))
)

function navigate() {
  window.location.href = presetEditorBaseUrl + props.preset.id + '/'
}

function formatThreshold(min: unknown, max: unknown): string {
  if (min == null && max == null) return '—'
  const minStr = min != null ? String(min) : '—'
  const maxStr = max != null ? String(max) : '—'
  return `${minStr} / ${maxStr}`
}

function highlightMatch(text: string, query: string): string {
  if (!query) return text
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length >= 2)
  if (tokens.length === 0) return text
  const pattern = tokens
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')
  return text.replace(regex, '<strong>$1</strong>')
}
</script>
