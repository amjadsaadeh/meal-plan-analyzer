import { createApp } from 'vue'
import ThresholdPresetEditorApp from './components/ThresholdPresetEditorApp.vue'
import type { I18n, Nutrient } from '../types/index'

const el = document.getElementById('threshold-preset-editor-app') as HTMLElement
const app = createApp(ThresholdPresetEditorApp)

app.provide('presetId', el.dataset.presetId as string)
app.provide('csrfToken', el.dataset.csrfToken as string)
app.provide('nutrients', JSON.parse(el.dataset.nutrients as string) as Nutrient[])
app.provide('i18n', JSON.parse(el.dataset.i18n as string) as I18n)
app.provide('presetListUrl', el.dataset.presetListUrl as string)

app.mount(el)
