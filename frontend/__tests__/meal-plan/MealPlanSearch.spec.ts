import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import MealPlanSearch from '../../src/components/meal-plan/MealPlanSearch.vue'

describe('MealPlanSearch', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('renders an input with id liveSearch', () => {
    const wrapper = mount(MealPlanSearch, { props: { modelValue: '' } })
    expect(wrapper.find('#liveSearch').exists()).toBe(true)
  })

  it('does not immediately emit search on input', async () => {
    const wrapper = mount(MealPlanSearch, { props: { modelValue: '' } })
    await wrapper.find('input').setValue('apple')
    expect(wrapper.emitted('search')).toBeFalsy()
  })

  it('emits search after debounce delay', async () => {
    const wrapper = mount(MealPlanSearch, { props: { modelValue: '' } })
    await wrapper.find('input').setValue('apple')
    vi.advanceTimersByTime(300)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('search')?.[0]).toEqual(['apple'])
  })
})
