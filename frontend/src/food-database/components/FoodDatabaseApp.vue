<template>
  <div>
    <div class="top-actions">
      <button class="btn-create" @click="createFood" :disabled="creating">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        {{ i18n.createFood }}
      </button>
      <div class="search-wrapper">
        <FoodSearchBar v-model="searchQuery" :placeholder="i18n.searchPlaceholder" />
      </div>
    </div>

    <div class="table-card" :class="{ 'is-loading': loading }">
      <FoodTable :foods="foods" :loading="loading" :search-query="searchQuery" />
      <Pagination
        v-if="totalPages > 1"
        :current-page="currentPage"
        :total-pages="totalPages"
        @update:current-page="onPageChange"
      />
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, inject, watch, onMounted } from 'vue'
import FoodSearchBar from './FoodSearchBar.vue'
import FoodTable from './FoodTable.vue'
import Pagination from './Pagination.vue'
import type { Food, I18n, PaginatedResponse } from '../../types/index'

const csrfToken = inject<string>('csrfToken')!
const foodEditorBaseUrl = inject<string>('foodEditorBaseUrl')!
const i18n = inject<I18n>('i18n')!

const foods = ref<Food[]>([])
const loading = ref(true)
const currentPage = ref(1)
const totalPages = ref(1)
const searchQuery = ref('')
const creating = ref(false)
const errorMsg = ref('')

const PAGE_SIZE = 100

async function fetchFoods(page: number, search: string) {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = new URLSearchParams({ page: String(page) })
    if (search) params.set('search', search)
    const res = await fetch(`/api/foods/?${params}`)
    if (!res.ok) throw new Error(String(res.status))
    const data: PaginatedResponse<Food> | Food[] = await res.json()
    foods.value = Array.isArray(data) ? data : (data.results ?? [])
    const count = Array.isArray(data) ? null : data.count
    totalPages.value = count != null ? Math.max(1, Math.ceil(count / PAGE_SIZE)) : 1
    currentPage.value = page
  } catch (e) {
    errorMsg.value = i18n.networkError ?? 'Network error'
  } finally {
    loading.value = false
  }
}

async function createFood() {
  creating.value = true
  errorMsg.value = ''
  try {
    const res = await fetch('/api/foods/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ name: i18n.newFoodName }),
    })
    if (!res.ok) throw new Error(String(res.status))
    const food: Food = await res.json()
    window.location.href = foodEditorBaseUrl + food.id + '/'
  } catch (e) {
    errorMsg.value = i18n.errorCreate ?? 'Error creating food'
  } finally {
    creating.value = false
  }
}

function onPageChange(page: number) {
  fetchFoods(page, searchQuery.value)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, (q) => {
  clearTimeout(searchTimer ?? undefined)
  if (q.length >= 2) {
    searchTimer = setTimeout(() => fetchFoods(1, q), 0)
  } else if (q.length === 0) {
    fetchFoods(1, '')
  }
})

onMounted(() => {
  fetchFoods(1, '')
})
</script>
