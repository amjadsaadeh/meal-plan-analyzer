<template>
  <tr class="meal-plan-row" @click="navigate">
    <td>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
      </svg>
    </td>
    <td class="meal-plan-name" v-html="highlightMatch(plan.name, searchQuery)"></td>
    <td>
      <div style="display: flex; gap: 4px; flex-wrap: wrap;">
        <template v-if="activeDays.length > 0">
          <DayBadge
            v-for="day in activeDays"
            :key="day.id"
            :plan-id="plan.id"
            :day="day"
          />
        </template>
        <span v-else class="no-data" style="padding: 0; font-size: 0.8rem;">{{ noDaysText }}</span>
      </div>
    </td>
    <td class="date-cell">{{ formatDate(plan.creation_date) }}</td>
    <td class="date-cell">{{ formatDateTime(plan.change_date) }}</td>
    <td class="actions-cell">
      <button class="delete-btn" @click.stop="onDelete">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          <line x1="10" y1="11" x2="10" y2="17"></line>
          <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>
      </button>
    </td>
  </tr>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import DayBadge from './DayBadge.vue'
import type { MealPlan } from '../../types/index'

const props = withDefaults(defineProps<{
  plan: MealPlan
  searchQuery?: string
  noDaysText?: string
}>(), {
  searchQuery: '',
  noDaysText: 'No days',
})

const requestDelete = inject<(pk: number, name: string) => void>('requestDelete')!

const activeDays = computed(() => (props.plan.days || []).filter(d => !d.removed))

function navigate() {
  window.location.href = `/meal-plan/${props.plan.id}/`
}

function onDelete() {
  requestDelete(props.plan.id, props.plan.name)
}

const SEMANTIC_KEYWORDS = new Set(['low', 'high', 'energy', 'cal', 'kcal', 'kj'])

function highlightMatch(text: string, query: string): string {
  if (!query) return text
  const tokens = query.toLowerCase().split(/\s+/)
    .filter(t => t.length >= 2 && !SEMANTIC_KEYWORDS.has(t))
  if (tokens.length === 0) return text
  const pattern = tokens.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  if (!pattern) return text
  const regex = new RegExp(`(${pattern})`, 'gi')
  return text.replace(regex, '<strong>$1</strong>')
}

function formatDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatDateTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  return `${date} ${time}`
}
</script>
