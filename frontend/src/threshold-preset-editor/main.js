import { createApp } from 'vue'
import ThresholdPresetEditorApp from './components/ThresholdPresetEditorApp.vue'

const el = document.getElementById('threshold-preset-editor-app')
const app = createApp(ThresholdPresetEditorApp)

app.provide('presetId', el.dataset.presetId)
app.provide('csrfToken', el.dataset.csrfToken)
app.provide('nutrients', JSON.parse(el.dataset.nutrients))
app.provide('i18n', JSON.parse(el.dataset.i18n))
app.provide('presetListUrl', el.dataset.presetListUrl)

app.mount(el)
