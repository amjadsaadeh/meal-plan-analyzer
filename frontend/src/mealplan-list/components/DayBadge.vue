<template>
  <a
    :href="`/meal-plan/${planId}/#day-${day.id}`"
    class="energy-badge"
    style="text-decoration: none;"
    @click.stop
  >
    {{ day.name }}
  </a>
</template>

<script setup>
defineProps({
  planId: { type: Number, required: true },
  day: { type: Object, required: true },
})
</script>
