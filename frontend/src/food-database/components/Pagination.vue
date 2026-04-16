<template>
  <div class="pagination">
    <span v-if="currentPage <= 1" class="page-link disabled">&laquo; {{ i18n.prev || '' }}</span>
    <a
      v-else
      class="page-link"
      href="#"
      @click.prevent="emit('update:currentPage', currentPage - 1)"
    >&laquo; {{ i18n.prev || '' }}</a>

    <template v-for="page in visiblePages" :key="page">
      <span v-if="page === currentPage" class="page-link active">{{ page }}</span>
      <a
        v-else
        class="page-link"
        href="#"
        @click.prevent="emit('update:currentPage', page)"
      >{{ page }}</a>
    </template>

    <span v-if="currentPage >= totalPages" class="page-link disabled">{{ i18n.next || '' }} &raquo;</span>
    <a
      v-else
      class="page-link"
      href="#"
      @click.prevent="emit('update:currentPage', currentPage + 1)"
    >{{ i18n.next || '' }} &raquo;</a>

    <div class="page-info" v-if="totalPages > 0">
      {{ i18n.pageInfo?.replace('{page}', String(currentPage)).replace('{total}', String(totalPages)) || `Page ${currentPage} of ${totalPages}` }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import type { I18n } from '../../types/index'

const i18n = inject<I18n>('i18n', {})

const props = defineProps<{
  currentPage: number
  totalPages: number
}>()

const emit = defineEmits<{
  'update:currentPage': [page: number]
}>()

const visiblePages = computed(() => {
  const pages: number[] = []
  for (let i = 1; i <= props.totalPages; i++) {
    if (Math.abs(i - props.currentPage) <= 2) {
      pages.push(i)
    }
  }
  return pages
})
</script>
