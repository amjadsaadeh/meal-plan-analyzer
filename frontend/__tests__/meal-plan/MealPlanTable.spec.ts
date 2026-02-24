import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import MealPlanTable from '../../src/components/meal-plan/MealPlanTable.vue'
import type { MealPlan } from '../../src/api/types'

const plans: MealPlan[] = [
  {
    id: 1, name: 'Plan A', subtitle: '',
    creation_date: '2024-01-01T00:00:00Z', change_date: '2024-02-01T00:00:00Z',
    days: [],
  },
  {
    id: 2, name: 'Plan B', subtitle: '',
    creation_date: '2024-01-02T00:00:00Z', change_date: '2024-02-02T00:00:00Z',
    days: [],
  },
]

describe('MealPlanTable', () => {
  it('renders one row per plan', () => {
    const wrapper = mount(MealPlanTable, { props: { plans } })
    expect(wrapper.findAll('.meal-plan-row')).toHaveLength(2)
  })

  it('shows empty state when no plans', () => {
    const wrapper = mount(MealPlanTable, { props: { plans: [] } })
    expect(wrapper.find('.no-data').exists()).toBe(true)
    expect(wrapper.text()).toContain('No meal plans found')
  })

  it('forwards navigate event from row', async () => {
    const wrapper = mount(MealPlanTable, { props: { plans } })
    await wrapper.findAll('.meal-plan-row')[0].trigger('click')
    expect(wrapper.emitted('navigate')?.[0]).toEqual([1])
  })

  it('forwards delete event from row', async () => {
    const wrapper = mount(MealPlanTable, { props: { plans } })
    await wrapper.findAll('.delete-btn')[0].trigger('click')
    expect(wrapper.emitted('delete')?.[0]).toEqual([1])
  })
})
