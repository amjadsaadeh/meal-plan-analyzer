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
        'mealplan-list': 'frontend/src/mealplan-list/main.ts',
        'mealplan-detail': 'frontend/src/mealplan-detail/main.ts',
        'food-database': 'frontend/src/food-database/main.ts',
        'food-editor': 'frontend/src/food-editor/main.ts',
        'threshold-preset-list':   'frontend/src/threshold-preset-list/main.ts',
        'threshold-preset-editor': 'frontend/src/threshold-preset-editor/main.ts',
      },
    },
  },
  server: {
    host: '0.0.0.0',
    origin: process.env.VITE_ORIGIN ?? 'http://localhost:5173',
    cors: true,
  },
})
