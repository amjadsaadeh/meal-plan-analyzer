import { createI18n } from 'vue-i18n'

const defaultMessages = {
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

declare global {
  interface Window {
    __I18N__?: typeof defaultMessages
  }
}

const messages = window.__I18N__ ?? defaultMessages

export const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: { en: messages },
})
