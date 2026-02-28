<template>
  <Teleport to="body">
    <div
      v-if="visible && results.length > 0"
      class="search-dropdown active"
      :style="{ top: position.top + 'px', left: position.left + 'px', width: position.width + 'px' }"
      @mousedown.prevent
    >
      <div
        v-for="food in results"
        :key="food.id"
        class="search-item"
        @mousedown.prevent="$emit('select', food)"
      >
        <div>
          <span class="name" v-html="highlightMatch(food.name, query)"></span>
          <span v-if="food.matched_alias" class="alias-badge">
            {{ i18n.aliasBadge }}
            <span class="alias-tooltip" v-html="highlightMatch(food.matched_alias, query)"></span>
          </span>
          <span class="code">{{ i18n.codeLabel }}: {{ food.bls_code }}</span>
        </div>
        <div class="energy-badge">{{ food.energy_in_kcal_per_100g }} kcal/100g</div>
      </div>
    </div>
    <div
      v-else-if="visible && results.length === 0 && query.length >= 2"
      class="search-dropdown active"
      :style="{ top: position.top + 'px', left: position.left + 'px', width: position.width + 'px' }"
    >
      <div class="search-item">{{ i18n.noResults }}</div>
    </div>
  </Teleport>
</template>

<script setup>
import { inject } from 'vue'

const i18n = inject('i18n')

defineProps({
  visible: { type: Boolean, default: false },
  position: { type: Object, default: () => ({ top: 0, left: 0, width: 300 }) },
  results: { type: Array, default: () => [] },
  query: { type: String, default: '' },
})

defineEmits(['select'])

function highlightMatch(text, query) {
  if (!query) return text
  const semanticKeywords = ['low', 'high', 'energy', 'cal', 'kcal', 'kj']
  const tokens = query.toLowerCase().split(/\s+/)
    .filter(t => t.length >= 2 && !semanticKeywords.includes(t))
  if (tokens.length === 0) return text
  const pattern = tokens.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')
  return text.replace(regex, '<strong>$1</strong>')
}
</script>
