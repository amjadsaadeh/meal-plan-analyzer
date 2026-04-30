<template>
  <div>
    <ConfirmDeleteModal
      :open="modalOpen"
      :plan-name="pendingDeleteName"
      :title="i18n.deleteModalTitle"
      :message="i18n.confirmDelete"
      :hint="i18n.deleteModalHint"
      :cancel-text="i18n.cancel"
      :confirm-text="i18n.deleteBtn"
      @confirm="doDelete"
      @cancel="modalOpen = false"
    />
    <div class="top-actions">
      <button class="btn-create" @click="createPlan">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        {{ i18n.createPlan }}
      </button>
      <div class="search-wrapper">
        <SearchBar v-model="searchQuery" :placeholder="i18n.searchPlaceholder" />
      </div>
    </div>

    <div class="table-card">
      <MealPlanTable
        :plans="plans"
        :search-query="searchQuery"
        :loading="loading"
        :col-name="i18n.colName"
        :col-days="i18n.colDays"
        :col-created="i18n.colCreated"
        :col-changed="i18n.colChanged"
        :no-data-text="i18n.noData"
        :no-days-text="i18n.noDays"
      />
      <Pagination
        v-if="totalPages > 1"
        :current-page="currentPage"
        :total-pages="totalPages"
        @update:current-page="onPageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, provide, inject } from 'vue'
import SearchBar from './SearchBar.vue'
import MealPlanTable from './MealPlanTable.vue'
import Pagination from './Pagination.vue'
import ConfirmDeleteModal from './ConfirmDeleteModal.vue'
import type { MealPlan, I18n, PaginatedResponse } from '../../types/index'

const csrfToken = inject<string>('csrfToken')!
const createUrl = inject<string>('createUrl')!
const i18n = inject<I18n>('i18n')!

async function createPlan() {
  const res = await fetch(createUrl, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
  })
  if (!res.ok) {
    alert(i18n.createPlan + ' failed')
    return
  }
  const data = await res.json()
  window.location.href = data.redirect
}

const plans = ref<MealPlan[]>([])
const loading = ref(true)
const searchQuery = ref('')
const currentPage = ref(1)
const totalPages = ref(1)

const modalOpen = ref(false)
const pendingDeletePk = ref<number | null>(null)
const pendingDeleteName = ref('')

let abortController: AbortController | null = null

async function fetchPlans() {
  if (abortController) abortController.abort()
  abortController = new AbortController()

  loading.value = true
  const params = new URLSearchParams()
  if (searchQuery.value) params.set('search', searchQuery.value)
  if (currentPage.value > 1) params.set('page', String(currentPage.value))

  try {
    const res = await fetch(`/api/mealplans/?${params}`, {
      headers: { Accept: 'application/json' },
      signal: abortController.signal,
    })
    const data: PaginatedResponse<MealPlan> = await res.json()
    plans.value = data.results
    totalPages.value = data.num_pages ?? 1
  } catch (err) {
    if ((err as Error).name !== 'AbortError') throw err
  } finally {
    loading.value = false
  }
}

function requestDelete(pk: number, name: string) {
  pendingDeletePk.value = pk
  pendingDeleteName.value = name
  modalOpen.value = true
}

async function doDelete() {
  modalOpen.value = false
  const pk = pendingDeletePk.value
  const res = await fetch(`/api/mealplans/${pk}/`, {
    method: 'DELETE',
    headers: { 'X-CSRFToken': csrfToken },
  })
  if (res.ok) {
    // If the deleted item was the last on this page, go back one page
    if (plans.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    } else {
      await fetchPlans()
    }
  } else {
    alert(i18n.errorDelete)
  }
}

provide('requestDelete', requestDelete)

function onPageChange(page: number) {
  currentPage.value = page
}

function syncToUrl() {
  const url = new URL(window.location.href)
  if (searchQuery.value) {
    url.searchParams.set('search', searchQuery.value)
  } else {
    url.searchParams.delete('search')
  }
  if (currentPage.value > 1) {
    url.searchParams.set('page', String(currentPage.value))
  } else {
    url.searchParams.delete('page')
  }
  window.history.pushState({}, '', url)
}

watch(searchQuery, () => {
  currentPage.value = 1
  syncToUrl()
  fetchPlans()
})

watch(currentPage, () => {
  syncToUrl()
  fetchPlans()
})

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  searchQuery.value = params.get('search') || ''
  currentPage.value = parseInt(params.get('page') || '1', 10)

  await fetchPlans()
})
</script>
