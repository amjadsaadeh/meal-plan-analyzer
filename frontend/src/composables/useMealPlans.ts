import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { listMealPlans, deleteMealPlan } from '../api/mealPlans'
import type { Ref } from 'vue'

export function useMealPlansQuery(search: Ref<string>, page: Ref<number>) {
  return useQuery({
    queryKey: ['mealplans', { search, page }],
    queryFn: () => listMealPlans(search.value, page.value),
  })
}

export function useDeleteMealPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteMealPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mealplans'] })
    },
  })
}
