<template>
  <div class="pagination">
    <span v-if="currentPage <= 1" class="page-link disabled">&laquo;</span>
    <a
      v-else
      class="page-link"
      href="#"
      @click.prevent="emit('update:currentPage', currentPage - 1)"
    >&laquo;</a>

    <template v-for="page in visiblePages" :key="page">
      <span v-if="page === currentPage" class="page-link active">{{ page }}</span>
      <a
        v-else
        class="page-link"
        href="#"
        @click.prevent="emit('update:currentPage', page)"
      >{{ page }}</a>
    </template>

    <span v-if="currentPage >= totalPages" class="page-link disabled">&raquo;</span>
    <a
      v-else
      class="page-link"
      href="#"
      @click.prevent="emit('update:currentPage', currentPage + 1)"
    >&raquo;</a>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: { type: Number, required: true },
  totalPages: { type: Number, required: true },
})

const emit = defineEmits(['update:currentPage'])

const visiblePages = computed(() => {
  const pages = []
  for (let i = 1; i <= props.totalPages; i++) {
    if (Math.abs(i - props.currentPage) <= 2) {
      pages.push(i)
    }
  }
  return pages
})
</script>
