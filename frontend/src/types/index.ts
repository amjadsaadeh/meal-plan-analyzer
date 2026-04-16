// API model types matching the Django backend

export interface Food {
  id: number
  bls_code: string
  name: string
  data_source: string
  matched_alias?: string | null
  energy_in_kcal_per_100g: number
  energy_in_kj_per_100g: number
  protein_in_g_per_100g: number
  fat_in_g_per_100g: number
  carbohydrate_in_g_per_100g: number
  fibre_in_g_per_100g: number
  water_in_g_per_100g: number
  iron_in_mg_per_100g: number
  sugar_in_g_per_100g: number
  omega3_in_g_per_100g: number
  vitc_in_mg_per_100g: number
  magnesium_in_mg_per_100g: number
  zinc_in_mg_per_100g: number
  vitb12_in_mug_per_100g: number
  vita_in_mug_per_100g: number
  calcium_in_mg_per_100g: number
  vitd_in_mug_per_100g: number
  vitb1_in_mg_per_100g: number
  vitb2_in_mg_per_100g: number
  vitb3_in_mg_per_100g: number
  vitb5_in_mg_per_100g: number
  vitb6_in_mug_per_100g: number
  biotin_in_mug_per_100g: number
  iodine_in_mug_per_100g: number
  copper_in_mug_per_100g: number
  manganese_in_mug_per_100g: number
  molybdenum_in_mug_per_100g: number
  [key: string]: unknown // allows dynamic nutrient key lookup via food[nut.food_key]
}

export interface FoodAlias {
  id: number
  food: number
  alias: string
}

export interface Threshold {
  min: number | null
  max: number | null
}

export type ThresholdMap = Record<string, Threshold>

export type MealType = 'breakfast' | 'lunch' | 'dinner'

export interface MealPlanFood {
  id: number
  meal_plan_day: number
  food: number
  food_data?: Food
  amount_in_g: number
  meal_type: MealType
  export_name: string
  _isDraft?: boolean // local-only flag used before server-side creation
}

export interface MealPlanDay {
  id: number
  name: string
  meal_plan: number | null
  creation_date: string
  change_date: string
  foods: MealPlanFood[]
  removed: boolean
}

export interface MealPlan {
  id: number
  name: string
  subtitle: string
  creation_date: string
  change_date: string
  visible_nutrients: string[]
  thresholds: ThresholdMap
  days: MealPlanDay[]
}

export interface ThresholdPreset {
  id: number
  name: string
  [key: string]: unknown // dynamic _min/_max fields per nutrient key
}

export interface BackgroundJob {
  id: string
  status: 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED'
  progress: number
  error_message: string
  created_at: string
  updated_at: string
}

export interface Nutrient {
  key: string
  label: string
  unit: string
  food_key: string
  precision: number
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
  num_pages?: number
  current_page?: number
}

// i18n dictionaries — keys vary per SPA but are always string → string
export type I18n = Record<string, string>

// Search state shared between MealPlanDetailApp and IngredientRow via provide/inject
export interface SearchPosition {
  top: number
  left: number
  width: number
}

export interface SearchState {
  visible: boolean
  position: SearchPosition
  results: Food[]
  query: string
  onSelect: ((food: Food) => void) | null
}

// Payload emitted by IngredientRow when a food+amount is confirmed
export interface IngredientSavePayload {
  food: Food
  amount_in_g: string
  existingId: number | null
}

// Payload emitted by IngredientRow when food search is activated
export interface ActivateSearchPayload {
  el: HTMLInputElement
  cb: (food: Food) => void
}
