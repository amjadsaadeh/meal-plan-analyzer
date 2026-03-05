import { createApp } from 'vue'
import FoodEditorApp from './components/FoodEditorApp.vue'

const el = document.getElementById('food-editor-app')
const app = createApp(FoodEditorApp)

app.provide('foodId', el.dataset.foodId)
app.provide('csrfToken', el.dataset.csrfToken)
app.provide('nutrients', JSON.parse(el.dataset.nutrients))
app.provide('i18n', JSON.parse(el.dataset.i18n))
app.provide('foodListUrl', el.dataset.foodListUrl)

app.mount(el)
