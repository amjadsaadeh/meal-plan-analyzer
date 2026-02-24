<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  currentPage: number
  totalPages: number
}>()

const emit = defineEmits<{
  change: [page: number]
}>()

const pages = computed(() => {
  const result: number[] = []
  for (let i = 1; i <= props.totalPages; i++) result.push(i)
  return result
})
</script>

<template>
  <nav v-if="totalPages > 1" class="pagination" aria-label="Pagination">
    <span
      class="page-link"
      :class="{ disabled: currentPage <= 1 }"
      @click="currentPage > 1 && emit('change', currentPage - 1)"
    >&laquo;</span>

    <span
      v-for="p in pages"
      :key="p"
      class="page-link"
      :class="{ active: p === currentPage }"
      @click="emit('change', p)"
    >{{ p }}</span>

    <span
      class="page-link"
      :class="{ disabled: currentPage >= totalPages }"
      @click="currentPage < totalPages && emit('change', currentPage + 1)"
    >&raquo;</span>
  </nav>
</template>
