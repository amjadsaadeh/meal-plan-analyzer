import { createApp } from 'vue'
import FoodDatabaseApp from './components/FoodDatabaseApp.vue'
import type { I18n } from '../types/index'

const el = document.getElementById('food-database-app') as HTMLElement
const app = createApp(FoodDatabaseApp)

app.provide('csrfToken', el.dataset.csrfToken as string)
app.provide('foodEditorBaseUrl', el.dataset.foodEditorBaseUrl as string)
app.provide('i18n', JSON.parse(el.dataset.i18n as string) as I18n)

app.mount(el)
