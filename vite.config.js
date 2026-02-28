import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  root: '.',
  base: '/static/',
  plugins: [vue()],
  build: {
    outDir: 'frontend/dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        'mealplan-list': 'frontend/src/mealplan-list/main.js',
        'mealplan-detail': 'frontend/src/mealplan-detail/main.js',
      },
    },
  },
  server: {
    host: '0.0.0.0',
    origin: process.env.VITE_ORIGIN ?? 'http://localhost:5173',
    cors: true,
  },
})
