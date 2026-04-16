import { createApp } from 'vue'
import FoodEditorApp from './components/FoodEditorApp.vue'
import type { I18n, Nutrient } from '../types/index'

const el = document.getElementById('food-editor-app') as HTMLElement
const app = createApp(FoodEditorApp)

app.provide('foodId', el.dataset.foodId as string)
app.provide('csrfToken', el.dataset.csrfToken as string)
app.provide('nutrients', JSON.parse(el.dataset.nutrients as string) as Nutrient[])
app.provide('i18n', JSON.parse(el.dataset.i18n as string) as I18n)
app.provide('foodListUrl', el.dataset.foodListUrl as string)

app.mount(el)
