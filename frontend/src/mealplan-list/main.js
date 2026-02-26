import { createApp } from 'vue'
import MealPlanApp from './components/MealPlanApp.vue'

const el = document.getElementById('meal-plan-app')
const app = createApp(MealPlanApp)

app.provide('csrfToken', el.dataset.csrfToken)
app.provide('createUrl', el.dataset.createUrl)
app.provide('i18n', JSON.parse(el.dataset.i18n))

app.mount(el)
