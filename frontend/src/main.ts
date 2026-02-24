import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import { i18n } from './i18n'
import router from './router'
import App from './App.vue'

const app = createApp(App)

app.use(createPinia())
app.use(VueQueryPlugin)
app.use(i18n)
app.use(router)

app.mount('#app')
