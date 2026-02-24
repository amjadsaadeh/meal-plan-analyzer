import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import BasePagination from '../../src/components/ui/BasePagination.vue'

describe('BasePagination', () => {
  it('renders nothing when totalPages <= 1', () => {
    const wrapper = mount(BasePagination, { props: { currentPage: 1, totalPages: 1 } })
    expect(wrapper.find('nav').exists()).toBe(false)
  })

  it('renders correct page links', () => {
    const wrapper = mount(BasePagination, { props: { currentPage: 2, totalPages: 3 } })
    const links = wrapper.findAll('.page-link')
    // prev + 3 pages + next = 5
    expect(links).toHaveLength(5)
    expect(links[2].text()).toBe('2')
  })

  it('emits change event on page click', async () => {
    const wrapper = mount(BasePagination, { props: { currentPage: 1, totalPages: 3 } })
    const links = wrapper.findAll('.page-link')
    await links[2].trigger('click') // page 2
    expect(wrapper.emitted('change')?.[0]).toEqual([2])
  })

  it('prev is disabled on first page', () => {
    const wrapper = mount(BasePagination, { props: { currentPage: 1, totalPages: 3 } })
    expect(wrapper.findAll('.page-link')[0].classes()).toContain('disabled')
  })

  it('next is disabled on last page', () => {
    const wrapper = mount(BasePagination, { props: { currentPage: 3, totalPages: 3 } })
    const links = wrapper.findAll('.page-link')
    expect(links[links.length - 1].classes()).toContain('disabled')
  })
})
