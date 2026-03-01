<template>
  <div class="sticky-bar" ref="barEl">
    <div class="sticky-bar-inner">
      <div class="sticky-plan-name">{{ planName }}</div>
      <div class="sticky-controls">
        <button class="col-select-btn sticky-col-btn" @click.stop="$emit('toggle-columns', $event.currentTarget)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
          {{ i18n.columns }}
        </button>
        <div class="sync-status">
          <span id="stickySyncText">{{ statusText }}</span>
          <div class="status-icon" id="stickySyncIcon" v-html="statusIcon"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'

const i18n = inject('i18n')

const props = defineProps({
  planName: { type: String, default: '' },
  syncStatus: { type: String, default: 'saved' },
  syncMessage: { type: String, default: '' },
  visibleNutrients: { type: Array, default: () => [] },
  nutrients: { type: Array, default: () => [] },
})

defineEmits(['toggle-columns'])

const statusText = computed(() => {
  if (props.syncStatus === 'saved') return i18n.saved
  if (props.syncStatus === 'error') return props.syncMessage || i18n.unsavedChanges
  return props.syncMessage || i18n.unsavedChanges
})

const statusIcon = computed(() => {
  if (props.syncStatus === 'saved') {
    return `<svg class="status-saved" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`
  }
  return `<svg class="status-pending" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>`
})
</script>
