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
        v-if="!isSearchMode && totalPages > 1"
        :current-page="currentPage"
        :total-pages="totalPages"
        @update:current-page="onPageChange"
      />
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup>
import { ref, inject, watch, onMounted } from 'vue'
import FoodSearchBar from './FoodSearchBar.vue'
import FoodTable from './FoodTable.vue'
import Pagination from './Pagination.vue'

const csrfToken = inject('csrfToken')
const foodEditorBaseUrl = inject('foodEditorBaseUrl')
const i18n = inject('i18n')

const foods = ref([])
const loading = ref(true)
const searchQuery = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const isSearchMode = ref(false)
const creating = ref(false)
const errorMsg = ref('')

const PAGE_SIZE = 100

async function fetchPage(page) {
  loading.value = true
  errorMsg.value = ''
  isSearchMode.value = false
  try {
    const res = await fetch(`/api/foods/?page=${page}`)
    if (!res.ok) throw new Error(res.status)
    const data = await res.json()
    foods.value = data.results ?? data
    totalPages.value = data.count != null ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1
    currentPage.value = page
  } catch (e) {
    errorMsg.value = i18n.networkError ?? 'Network error'
  } finally {
    loading.value = false
  }
}

async function doSearch(query) {
  loading.value = true
  errorMsg.value = ''
  isSearchMode.value = true
  currentPage.value = 1
  try {
    const res = await fetch(`/api/foods/?search=${encodeURIComponent(query)}`)
    if (!res.ok) throw new Error(res.status)
    const data = await res.json()
    // search returns plain array (no pagination)
    foods.value = Array.isArray(data) ? data : (data.results ?? [])
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
    if (!res.ok) throw new Error(res.status)
    const food = await res.json()
    window.location.href = foodEditorBaseUrl + food.id + '/'
  } catch (e) {
    errorMsg.value = i18n.errorCreate ?? 'Error creating food'
  } finally {
    creating.value = false
  }
}

function onPageChange(page) {
  currentPage.value = page
  fetchPage(page)
}

let searchTimer = null
watch(searchQuery, (q) => {
  clearTimeout(searchTimer)
  if (q.length >= 2) {
    searchTimer = setTimeout(() => doSearch(q), 0) // already debounced in FoodSearchBar
  } else {
    isSearchMode.value = false
    if (q.length === 0) {
      fetchPage(currentPage.value)
    }
  }
})

onMounted(() => {
  fetchPage(1)
})
</script>
