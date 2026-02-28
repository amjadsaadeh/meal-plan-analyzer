import { createApp } from 'vue'
import MealPlanDetailApp from './components/MealPlanDetailApp.vue'

const el = document.getElementById('meal-plan-detail-app')
if (!el) throw new Error('Mount element #meal-plan-detail-app not found')

const app = createApp(MealPlanDetailApp)

app.provide('planId', el.dataset.planId)
app.provide('csrfToken', el.dataset.csrfToken)
app.provide('nutrients', JSON.parse(el.dataset.nutrients))
app.provide('i18n', JSON.parse(el.dataset.i18n))
app.provide('pdfUrl', el.dataset.pdfUrl)
app.provide('previewUrl', el.dataset.previewUrl)
app.provide('planListUrl', el.dataset.planListUrl)

app.mount(el)
