import { afterEach, describe, expect, it, vi } from 'vitest'
import { THEME_KEY, applyTheme, currentTheme, initialTheme } from './theme'

function mockSystem(dark: boolean) {
  vi.stubGlobal('matchMedia', (q: string) => ({ matches: dark && q.includes('dark') }))
}

afterEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
  delete document.documentElement.dataset.theme
})

describe('initialTheme', () => {
  it('follows the system when nothing is stored', () => {
    mockSystem(true)
    expect(initialTheme()).toBe('dark')
    mockSystem(false)
    expect(initialTheme()).toBe('light')
  })

  it('defaults to light without matchMedia', () => {
    vi.stubGlobal('matchMedia', undefined)
    expect(initialTheme()).toBe('light')
  })

  it('prefers the stored choice over the system', () => {
    mockSystem(true)
    localStorage.setItem(THEME_KEY, 'light')
    expect(initialTheme()).toBe('light')
  })

  it('ignores an unknown stored value', () => {
    mockSystem(false)
    localStorage.setItem(THEME_KEY, 'sepia')
    expect(initialTheme()).toBe('light')
  })
})

describe('applyTheme', () => {
  it('sets data-theme and remembers the choice', () => {
    applyTheme('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(currentTheme()).toBe('dark')
    expect(localStorage.getItem(THEME_KEY)).toBe('dark')
  })

  it('still switches when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    applyTheme('dark')
    expect(currentTheme()).toBe('dark')
    vi.restoreAllMocks()
  })
})
