import { config } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'

// Set up window.__I18N__ fallback for tests
window.__I18N__ = {
  mealPlans: 'Meal Plans',
  createNewPlan: 'Create New Plan',
  searchPlansPlaceholder: 'Search plans...',
  columnName: 'Name',
  columnDays: 'Days',
  columnCreated: 'Created',
  columnLastChanged: 'Last Changed',
  noDays: 'No days',
  noMealPlansFound: 'No meal plans found.',
  confirmDeletePlan: 'Are you sure you want to delete this meal plan?',
  errorDeletingPlan: 'Error deleting plan',
  cancel: 'Cancel',
  delete: 'Delete',
}

const testI18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: { en: window.__I18N__ },
})

config.global.plugins = [
  testI18n,
  createPinia(),
  VueQueryPlugin,
]
