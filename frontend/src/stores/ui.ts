import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const search = ref('')
  const page = ref(1)

  function setSearch(s: string) {
    search.value = s
    page.value = 1
  }

  function setPage(n: number) {
    page.value = n
  }

  return { search, page, setSearch, setPage }
})
