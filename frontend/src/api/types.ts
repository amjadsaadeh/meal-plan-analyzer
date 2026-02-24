export interface MealPlanDay {
  id: number
  name: string
  creation_date: string
  change_date: string
}

export interface MealPlan {
  id: number
  name: string
  subtitle: string
  creation_date: string
  change_date: string
  days: MealPlanDay[]
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
