<template>
  <input
    id="liveSearch"
    type="text"
    name="search"
    class="search-bar"
    :placeholder="placeholder"
    :value="modelValue"
    autocomplete="off"
    @input="onInput"
    @keydown.enter.prevent
  />
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue?: string
  placeholder?: string
}>(), {
  modelValue: '',
  placeholder: '',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

let timer: ReturnType<typeof setTimeout> | null = null

function onInput(e: Event) {
  clearTimeout(timer ?? undefined)
  const value = (e.target as HTMLInputElement).value
  timer = setTimeout(() => {
    emit('update:modelValue', value)
  }, 300)
}
</script>
