import { createApp } from 'vue'
import ThresholdPresetApp from './components/ThresholdPresetApp.vue'
import type { I18n, Nutrient } from '../types/index'

const el = document.getElementById('threshold-preset-list-app') as HTMLElement
const app = createApp(ThresholdPresetApp)

app.provide('csrfToken', el.dataset.csrfToken as string)
app.provide('presetEditorBaseUrl', el.dataset.presetEditorBaseUrl as string)
app.provide('nutrients', JSON.parse(el.dataset.nutrients as string) as Nutrient[])
app.provide('i18n', JSON.parse(el.dataset.i18n as string) as I18n)

app.mount(el)
