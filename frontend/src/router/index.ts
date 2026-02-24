import { createRouter, createWebHistory } from 'vue-router'
import MealPlanListView from '../views/MealPlanListView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: MealPlanListView },
  ],
})

export default router
