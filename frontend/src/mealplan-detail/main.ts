import { createApp } from 'vue'
import MealPlanDetailApp from './components/MealPlanDetailApp.vue'
import type { I18n, Nutrient } from '../types/index'

const el = document.getElementById('meal-plan-detail-app') as HTMLElement
if (!el) throw new Error('Mount element #meal-plan-detail-app not found')

const app = createApp(MealPlanDetailApp)

app.provide('planId', el.dataset.planId as string)
app.provide('csrfToken', el.dataset.csrfToken as string)
app.provide('nutrients', JSON.parse(el.dataset.nutrients as string) as Nutrient[])
app.provide('i18n', JSON.parse(el.dataset.i18n as string) as I18n)
app.provide('pdfUrl', el.dataset.pdfUrl as string)
app.provide('previewUrl', el.dataset.previewUrl as string)
app.provide('planListUrl', el.dataset.planListUrl as string)

app.mount(el)
