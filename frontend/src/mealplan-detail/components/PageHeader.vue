<template>
  <div class="header-top" ref="headerEl">
    <div class="plan-title-wrapper">
      <div class="title-container">
        <h1
          id="planName"
          ref="titleEl"
          class="editable-title"
          contenteditable="true"
          :placeholder="i18n.editName"
          @input="onInput"
          @blur="onBlur"
          @keydown.enter.prevent="titleEl.blur()"
        ></h1>
        <button class="edit-icon-btn" @click="titleEl.focus()" :title="i18n.editName">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
        </button>
      </div>
    </div>
    <div class="header-info">
      <span class="plan-id">{{ i18n.planNo }} {{ plan.id }}</span>
      <div class="sync-status" id="syncStatus">
        <span id="syncText">{{ statusText }}</span>
        <div class="status-icon" id="syncIcon" v-html="statusIcon"></div>
      </div>
      <div style="display: flex; gap: 8px;">
        <a v-if="previewUrl" :href="previewUrl" target="_blank" rel="noopener" class="btn btn-pdf">{{ i18n.exportPdf }}</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from 'vue'

const i18n = inject('i18n')

const props = defineProps({
  plan: { type: Object, required: true },
  syncStatus: { type: String, default: 'saved' },
  syncMessage: { type: String, default: '' },
  pdfUrl: { type: String, default: '' },
  previewUrl: { type: String, default: '' },
})

const emit = defineEmits(['update:name'])

const titleEl = ref(null)

onMounted(() => {
  if (titleEl.value) titleEl.value.textContent = props.plan.name
})

watch(() => props.plan.name, (name) => {
  if (titleEl.value && titleEl.value.textContent !== name) {
    titleEl.value.textContent = name
  }
})

function onInput(e) {
  emit('update:name', e.target.textContent.trim())
}

function onBlur(e) {
  const name = e.target.textContent.trim()
  if (!name) {
    e.target.textContent = props.plan.name
    return
  }
  emit('update:name', name)
}

const statusText = computed(() => {
  if (props.syncStatus === 'saved') return i18n.saved
  return props.syncMessage || i18n.unsavedChanges
})

const statusIcon = computed(() => {
  if (props.syncStatus === 'saved') {
    return `<svg class="status-saved" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`
  }
  return `<svg class="status-pending" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>`
})
</script>
