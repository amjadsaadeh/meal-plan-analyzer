import { createApp } from 'vue'
import FoodDatabaseApp from './components/FoodDatabaseApp.vue'

const el = document.getElementById('food-database-app')
const app = createApp(FoodDatabaseApp)

app.provide('csrfToken', el.dataset.csrfToken)
app.provide('foodEditorBaseUrl', el.dataset.foodEditorBaseUrl)
app.provide('i18n', JSON.parse(el.dataset.i18n))

app.mount(el)
