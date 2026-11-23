import { act, fireEvent, render, renderHook, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Link, cameFromSite, navigate, parseRoute, usePathname } from './router'

afterEach(() => {
  window.history.replaceState(null, '', '/')
  vi.restoreAllMocks()
})

describe('parseRoute', () => {
  it.each([
    ['/', { page: 'home' }],
    ['', { page: 'home' }],
    ['/styleguide', { page: 'styleguide' }],
    ['/styleguide/', { page: 'styleguide' }],
    ['/connexion', { page: 'login' }],
    ['/connexion/', { page: 'login' }],
    ['/film/266', { page: 'film', tmdbId: 266 }],
    ['/film/266/', { page: 'film', tmdbId: 266 }],
    ['/film/abc', { page: 'not-found' }],
    ['/film/0', { page: 'not-found' }],
    ['/film/012', { page: 'not-found' }],
    ['/film/12a', { page: 'not-found' }],
    ['/film/', { page: 'not-found' }],
    ['/film/99999999999', { page: 'not-found' }],
    ['/nimporte', { page: 'not-found' }],
  ])('%s', (pathname, route) => {
    expect(parseRoute(pathname)).toEqual(route)
  })
})

describe('navigate / usePathname', () => {
  it('pushes a history entry and the hook follows', () => {
    const push = vi.spyOn(window.history, 'pushState')
    const { result } = renderHook(() => usePathname())
    expect(result.current).toBe('/')
    act(() => navigate('/film/266'))
    expect(push).toHaveBeenCalledTimes(1)
    expect(window.location.pathname).toBe('/film/266')
    expect(result.current).toBe('/film/266')
    expect(cameFromSite()).toBe(true)
  })

  it('reads the path again on popstate', () => {
    const { result } = renderHook(() => usePathname())
    act(() => {
      window.history.pushState(null, '', '/film/1')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    expect(result.current).toBe('/film/1')
    expect(cameFromSite()).toBe(false)
  })
})

describe('Link', () => {
  it('navigates in place on a plain click', () => {
    render(<Link href="/film/266">le mépris</Link>)
    fireEvent.click(screen.getByRole('link', { name: 'le mépris' }))
    expect(window.location.pathname).toBe('/film/266')
  })

  it('lets the browser handle a modified click (new tab)', () => {
    const push = vi.spyOn(window.history, 'pushState')
    render(<Link href="/film/266">le mépris</Link>)
    fireEvent.click(screen.getByRole('link'), { ctrlKey: true })
    fireEvent.click(screen.getByRole('link'), { metaKey: true })
    expect(push).not.toHaveBeenCalled()
  })
})
