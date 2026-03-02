<template>
  <div class="day-section" :data-day-id="day.id" :id="`day-${day.id}`">
    <div class="day-title-container">
      <h2
        ref="dayTitleEl"
        class="editable-day-title"
        contenteditable="true"
        @blur="onDayNameBlur"
        @keydown.enter.prevent="dayTitleEl.blur()"
      ></h2>
      <button class="edit-icon-btn" @click="dayTitleEl.focus()" :title="i18n.editDayName">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
      </button>
      <button
        class="delete-btn"
        @click="emit('delete')"
        :title="i18n.deleteDay2"
        style="opacity: 0.3; transition: opacity 0.2s;"
        @mouseenter="$event.currentTarget.style.opacity = 1"
        @mouseleave="$event.currentTarget.style.opacity = 0.3"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          <line x1="10" y1="11" x2="10" y2="17"></line>
          <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>
      </button>
    </div>

    <div class="content-layout">
      <div class="meal-sections-wrapper">
        <MealSection
          v-for="mealType in ['breakfast', 'lunch', 'dinner']"
          :key="mealType"
          :day-id="day.id"
          :meal-type="mealType"
          :foods="dayFoods(mealType)"
          :nutrients="nutrients"
          :visible-nutrients="visibleNutrients"
          @food-saved="emit('food-saved', $event)"
          @food-deleted="emit('food-deleted', $event)"
          @request-delete="emit('request-delete', $event)"
          @activate-search="emit('activate-search', $event.el, $event.cb)"
          @deactivate-search="emit('deactivate-search')"
        />
      </div>

      <div class="side-panel">
        <DaySidePanel
          :day="day"
          :nutrients="nutrients"
          :visible-nutrients="visibleNutrients"
          :thresholds="thresholds"
          :all-foods="day.foods"
          @open-save-preset="emit('open-save-preset')"
          @update-threshold="emit('update-threshold', $event.key, $event.type, $event.value)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, inject } from 'vue'
import MealSection from './MealSection.vue'
import DaySidePanel from './DaySidePanel.vue'

const i18n = inject('i18n')

const props = defineProps({
  day: { type: Object, required: true },
  nutrients: { type: Array, default: () => [] },
  visibleNutrients: { type: Array, default: () => [] },
  thresholds: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:name', 'delete', 'food-saved', 'food-deleted', 'open-save-preset', 'update-threshold', 'activate-search', 'deactivate-search', 'request-delete'])

const dayTitleEl = ref(null)

onMounted(() => {
  if (dayTitleEl.value) dayTitleEl.value.textContent = props.day.name
})

watch(() => props.day.name, (name) => {
  if (dayTitleEl.value && dayTitleEl.value.textContent !== name) {
    dayTitleEl.value.textContent = name
  }
})

function onDayNameBlur(e) {
  const name = e.target.textContent.trim()
  if (!name) {
    e.target.textContent = props.day.name
    return
  }
  if (name !== props.day.name) {
    emit('update:name', name)
  }
}

function dayFoods(mealType) {
  return (props.day.foods || []).filter(f => f.meal_type === mealType)
}
</script>
