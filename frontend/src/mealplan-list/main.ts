import { createApp } from 'vue'
import MealPlanApp from './components/MealPlanApp.vue'
import type { I18n } from '../types/index'

const el = document.getElementById('meal-plan-app') as HTMLElement
const app = createApp(MealPlanApp)

app.provide('csrfToken', el.dataset.csrfToken as string)
app.provide('createUrl', el.dataset.createUrl as string)
app.provide('i18n', JSON.parse(el.dataset.i18n as string) as I18n)

app.mount(el)
