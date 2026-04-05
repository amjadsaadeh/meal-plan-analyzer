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
      <FoodTable :foods="visibleFoods" :loading="loading" :search-query="searchQuery" />
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

<script setup>
import { ref, computed, inject, watch, onMounted } from 'vue'
import FoodSearchBar from './FoodSearchBar.vue'
import FoodTable from './FoodTable.vue'
import Pagination from './Pagination.vue'

const csrfToken = inject('csrfToken')
const foodEditorBaseUrl = inject('foodEditorBaseUrl')
const i18n = inject('i18n')

// Browse-mode state
const browseResults = ref([])
const browseTotalPages = ref(1)

// Search-mode state (all results fetched at once; paginated client-side)
const searchResults = ref([])
const isSearchMode = ref(false)

const currentPage = ref(1)
const loading = ref(true)
const creating = ref(false)
const errorMsg = ref('')

const PAGE_SIZE = 100

const totalPages = computed(() => {
  if (isSearchMode.value) {
    return Math.max(1, Math.ceil(searchResults.value.length / PAGE_SIZE))
  }
  return browseTotalPages.value
})

const visibleFoods = computed(() => {
  if (isSearchMode.value) {
    const start = (currentPage.value - 1) * PAGE_SIZE
    return searchResults.value.slice(start, start + PAGE_SIZE)
  }
  return browseResults.value
})

async function fetchPage(page) {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch(`/api/foods/?page=${page}`)
    if (!res.ok) throw new Error(res.status)
    const data = await res.json()
    browseResults.value = data.results ?? data
    browseTotalPages.value = data.count != null ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1
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
    searchResults.value = Array.isArray(data) ? data : (data.results ?? [])
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
  if (!isSearchMode.value) {
    fetchPage(page)
  }
  // In search mode: visibleFoods is a computed slice — no network request needed
}

let searchTimer = null
watch(searchQuery, (q) => {
  clearTimeout(searchTimer)
  if (q.length >= 2) {
    searchTimer = setTimeout(() => doSearch(q), 0) // already debounced in FoodSearchBar
  } else {
    isSearchMode.value = false
    searchResults.value = []
    if (q.length === 0) {
      fetchPage(1)
    }
  }
})

onMounted(() => {
  fetchPage(1)
})
</script>
