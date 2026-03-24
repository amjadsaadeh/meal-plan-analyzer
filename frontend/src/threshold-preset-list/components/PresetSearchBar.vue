<template>
  <input
    type="text"
    class="search-bar"
    :placeholder="placeholder"
    :value="modelValue"
    autocomplete="off"
    @input="onInput"
    @keydown.enter.prevent
  />
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

let timer = null

function onInput(e) {
  clearTimeout(timer)
  const value = e.target.value
  timer = setTimeout(() => {
    emit('update:modelValue', value)
  }, 300)
}
</script>
