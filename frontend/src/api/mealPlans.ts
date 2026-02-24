import client from './client'
import type { MealPlan, Paginated } from './types'

export async function listMealPlans(search = '', page = 1): Promise<Paginated<MealPlan>> {
  const params: Record<string, string | number> = { page, page_size: 10 }
  if (search) params.search = search
  const { data } = await client.get<Paginated<MealPlan>>('mealplans/', { params })
  return data
}

export async function deleteMealPlan(id: number): Promise<void> {
  await client.delete(`mealplans/${id}/`)
}
