<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import BaseBadge from '../ui/BaseBadge.vue'
import type { MealPlan } from '../../api/types'

const { t } = useI18n()

const props = defineProps<{ plan: MealPlan }>()

const emit = defineEmits<{
  navigate: [id: number]
  delete: [id: number]
}>()

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString()
}

function handleRowClick(event: MouseEvent) {
  if ((event.target as HTMLElement).closest('.delete-btn')) return
  emit('navigate', props.plan.id)
}
</script>

<template>
  <tr class="meal-plan-row" @click="handleRowClick" style="cursor: pointer;">
    <td>{{ plan.name }}</td>
    <td>
      <span v-if="plan.days.length === 0" class="text-dim">{{ t('noDays') }}</span>
      <template v-else>
        <BaseBadge v-for="day in plan.days" :key="day.id" :label="day.name" />
      </template>
    </td>
    <td>{{ formatDate(plan.creation_date) }}</td>
    <td>{{ formatDate(plan.change_date) }}</td>
    <td>
      <button
        class="delete-btn"
        @click.stop="emit('delete', plan.id)"
        :aria-label="`Delete ${plan.name}`"
      >✕</button>
    </td>
  </tr>
</template>
