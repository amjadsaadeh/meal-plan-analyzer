import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import MealPlanRow from '../../src/components/meal-plan/MealPlanRow.vue'
import type { MealPlan } from '../../src/api/types'

const plan: MealPlan = {
  id: 1,
  name: 'Test Plan',
  subtitle: '',
  creation_date: '2024-01-01T00:00:00Z',
  change_date: '2024-02-01T00:00:00Z',
  days: [
    { id: 10, name: 'Day 1', creation_date: '2024-01-01T00:00:00Z', change_date: '2024-01-01T00:00:00Z' },
  ],
}

describe('MealPlanRow', () => {
  it('renders plan name', () => {
    const wrapper = mount(MealPlanRow, { props: { plan } })
    expect(wrapper.text()).toContain('Test Plan')
  })

  it('renders day badge', () => {
    const wrapper = mount(MealPlanRow, { props: { plan } })
    expect(wrapper.find('.badge').text()).toBe('Day 1')
  })

  it('has meal-plan-row class', () => {
    const wrapper = mount(MealPlanRow, { props: { plan } })
    expect(wrapper.classes()).toContain('meal-plan-row')
  })

  it('emits navigate on row click', async () => {
    const wrapper = mount(MealPlanRow, { props: { plan } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('navigate')?.[0]).toEqual([1])
  })

  it('emits delete on delete button click', async () => {
    const wrapper = mount(MealPlanRow, { props: { plan } })
    await wrapper.find('.delete-btn').trigger('click')
    expect(wrapper.emitted('delete')?.[0]).toEqual([1])
  })

  it('shows no-days text when days is empty', () => {
    const wrapper = mount(MealPlanRow, { props: { plan: { ...plan, days: [] } } })
    expect(wrapper.text()).toContain('No days')
  })
})
