import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import BaseModal from '../../src/components/ui/BaseModal.vue'

describe('BaseModal', () => {
  it('is not visible when open=false', () => {
    const wrapper = mount(BaseModal, { props: { open: false } })
    expect(wrapper.find('.modal-backdrop').exists()).toBe(false)
  })

  it('is visible when open=true', () => {
    const wrapper = mount(BaseModal, {
      props: { open: true },
      attachTo: document.body,
    })
    expect(document.querySelector('.modal-backdrop')).toBeTruthy()
    wrapper.unmount()
  })

  it('emits confirm when confirm button clicked', async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true, confirmLabel: 'OK' },
      attachTo: document.body,
    })
    await document.querySelector<HTMLButtonElement>('[data-testid="confirm-delete-btn"]')!.click()
    expect(wrapper.emitted('confirm')).toBeTruthy()
    wrapper.unmount()
  })

  it('emits cancel when cancel button clicked', async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true, cancelLabel: 'No' },
      attachTo: document.body,
    })
    const buttons = document.querySelectorAll<HTMLButtonElement>('.btn-secondary')
    await buttons[buttons.length - 1].click()
    expect(wrapper.emitted('cancel')).toBeTruthy()
    wrapper.unmount()
  })
})
