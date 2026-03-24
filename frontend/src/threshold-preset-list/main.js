import { createApp } from 'vue'
import ThresholdPresetApp from './components/ThresholdPresetApp.vue'

const el = document.getElementById('threshold-preset-list-app')
const app = createApp(ThresholdPresetApp)

app.provide('csrfToken', el.dataset.csrfToken)
app.provide('presetEditorBaseUrl', el.dataset.presetEditorBaseUrl)
app.provide('nutrients', JSON.parse(el.dataset.nutrients))
app.provide('i18n', JSON.parse(el.dataset.i18n))

app.mount(el)
