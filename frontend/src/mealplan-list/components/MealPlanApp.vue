<template>
  <div>
    <div class="top-actions">
      <a :href="createUrl" class="btn-create">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        {{ i18n.createPlan }}
      </a>
      <div class="search-wrapper">
        <SearchBar v-model="searchQuery" :placeholder="i18n.searchPlaceholder" />
      </div>
    </div>

    <div class="table-card">
      <MealPlanTable
        :plans="paginatedPlans"
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

<script setup>
import { ref, computed, watch, onMounted, provide, inject } from 'vue'
import SearchBar from './SearchBar.vue'
import MealPlanTable from './MealPlanTable.vue'
import Pagination from './Pagination.vue'

const csrfToken = inject('csrfToken')
const createUrl = inject('createUrl')
const i18n = inject('i18n')

const plans = ref([])
const loading = ref(true)
const searchQuery = ref('')
const currentPage = ref(1)

const PAGE_SIZE = 10

const filteredPlans = computed(() => {
  if (!searchQuery.value) return plans.value
  const q = searchQuery.value.toLowerCase()
  return plans.value.filter(p => p.name.toLowerCase().includes(q))
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredPlans.value.length / PAGE_SIZE)))

const paginatedPlans = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredPlans.value.slice(start, start + PAGE_SIZE)
})

async function fetchAllPlans() {
  loading.value = true
  const all = []
  let url = '/api/mealplans/'
  while (url) {
    const res = await fetch(url, { headers: { Accept: 'application/json' } })
    const data = await res.json()
    all.push(...data.results)
    url = data.next
  }
  plans.value = all
  loading.value = false
}

async function deletePlan(pk) {
  if (!confirm(i18n.confirmDelete)) return
  const res = await fetch(`/api/mealplans/${pk}/`, {
    method: 'DELETE',
    headers: { 'X-CSRFToken': csrfToken },
  })
  if (res.ok) {
    plans.value = plans.value.filter(p => p.id !== pk)
    if (currentPage.value > totalPages.value) {
      currentPage.value = totalPages.value
    }
  } else {
    alert(i18n.errorDelete)
  }
}

provide('deletePlan', deletePlan)

function onPageChange(page) {
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
    url.searchParams.set('page', currentPage.value)
  } else {
    url.searchParams.delete('page')
  }
  window.history.pushState({}, '', url)
}

watch(searchQuery, () => {
  currentPage.value = 1
  syncToUrl()
})

watch(currentPage, () => {
  syncToUrl()
})

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  searchQuery.value = params.get('search') || ''
  currentPage.value = parseInt(params.get('page') || '1', 10)

  await fetchAllPlans()
})
</script>
