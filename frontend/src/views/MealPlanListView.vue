<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMealPlansQuery, useDeleteMealPlan } from '../composables/useMealPlans'
import { useUiStore } from '../stores/ui'
import MealPlanSearch from '../components/meal-plan/MealPlanSearch.vue'
import MealPlanTable from '../components/meal-plan/MealPlanTable.vue'
import MealPlanDeleteModal from '../components/meal-plan/MealPlanDeleteModal.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseButton from '../components/ui/BaseButton.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const ui = useUiStore()

// Sync UI store from URL params on mount
ui.search = (route.query.search as string) ?? ''
ui.page = Number(route.query.page) || 1

// Sync URL params when store changes
watch([() => ui.search, () => ui.page], ([search, page]) => {
  router.replace({ query: { ...(search ? { search } : {}), ...(page > 1 ? { page: String(page) } : {}) } })
})

const { data, isLoading, isError } = useMealPlansQuery(
  computed(() => ui.search),
  computed(() => ui.page),
)

const totalPages = computed(() => {
  if (!data.value) return 0
  return Math.ceil(data.value.count / 10)
})

// Delete flow
const deleteMutation = useDeleteMealPlan()
const pendingDeleteId = ref<number | null>(null)
const showDeleteModal = ref(false)

function onDeleteRequest(id: number) {
  pendingDeleteId.value = id
  showDeleteModal.value = true
}

function onDeleteConfirm() {
  if (pendingDeleteId.value !== null) {
    deleteMutation.mutate(pendingDeleteId.value, {
      onSuccess: () => {
        showDeleteModal.value = false
        pendingDeleteId.value = null
      },
    })
  }
}

function onDeleteCancel() {
  showDeleteModal.value = false
  pendingDeleteId.value = null
}

function navigateToPlan(id: number) {
  window.location.href = `/meal-plan/${id}/`
}

function createNewPlan() {
  window.location.href = '/meal-plan/new/'
}
</script>

<template>
  <div class="meal-plan-list-view">
    <div class="list-header">
      <h1>{{ t('mealPlans') }}</h1>
      <BaseButton variant="primary" @click="createNewPlan">
        {{ t('createNewPlan') }}
      </BaseButton>
    </div>

    <MealPlanSearch
      v-model="ui.search"
      @search="ui.setSearch($event)"
    />

    <div v-if="isLoading">…</div>
    <div v-else-if="isError">Error loading meal plans.</div>
    <template v-else>
      <MealPlanTable
        :plans="data?.results ?? []"
        @navigate="navigateToPlan"
        @delete="onDeleteRequest"
      />

      <BasePagination
        :current-page="ui.page"
        :total-pages="totalPages"
        @change="ui.setPage($event)"
      />
    </template>

    <MealPlanDeleteModal
      :open="showDeleteModal"
      @confirm="onDeleteConfirm"
      @cancel="onDeleteCancel"
    />
  </div>
</template>
