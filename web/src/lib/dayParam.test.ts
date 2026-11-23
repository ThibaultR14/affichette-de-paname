import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { readDayParam, useSelectedDay, withDayParam } from './dayParam'

describe('readDayParam', () => {
  it('reads ?jour=', () => {
    expect(readDayParam('?jour=2026-11-24&salles=champo')).toBe('2026-11-24')
    expect(readDayParam('?salles=champo')).toBeNull()
    expect(readDayParam('')).toBeNull()
  })
})

describe('withDayParam', () => {
  it('sets or removes jour and keeps the other parameters', () => {
    expect(withDayParam('', '2026-11-24')).toBe('?jour=2026-11-24')
    expect(withDayParam('?salles=champo&jour=2026-11-23', '2026-11-24')).toBe(
      '?salles=champo&jour=2026-11-24',
    )
    expect(withDayParam('?jour=nope&ugc=1', null)).toBe('?ugc=1')
    expect(withDayParam('?jour=nope', null)).toBe('')
  })
})

describe('useSelectedDay', () => {
  // Monday 23 Nov 2026, 11:00 in Paris.
  const NOW = new Date('2026-11-23T10:00:00Z')

  function goTo(url: string) {
    window.history.replaceState(null, '', url)
  }

  beforeEach(() => {
    vi.useFakeTimers({ now: NOW })
    goTo('/')
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    goTo('/')
  })

  it('defaults to today and leaves a clean URL alone', () => {
    const replace = vi.spyOn(window.history, 'replaceState')
    const { result } = renderHook(() => useSelectedDay())
    expect(result.current.today).toBe('2026-11-23')
    expect(result.current.day).toBe('2026-11-23')
    expect(result.current.week).toHaveLength(7)
    expect(result.current.week[6]).toBe('2026-11-29')
    expect(replace).not.toHaveBeenCalled()
  })

  it('opens the day given by ?jour=', () => {
    goTo('/?jour=2026-11-29')
    const { result } = renderHook(() => useSelectedDay())
    expect(result.current.day).toBe('2026-11-29')
    expect(window.location.search).toBe('?jour=2026-11-29')
  })

  it.each(['2026-11-22', '2026-11-30', 'demain', '2026-13-40'])(
    'falls back to today and removes ?jour=%s from the URL',
    (param) => {
      goTo(`/?ugc=1&jour=${param}#top`)
      const { result } = renderHook(() => useSelectedDay())
      expect(result.current.day).toBe('2026-11-23')
      expect(window.location.search).toBe('?ugc=1')
      expect(window.location.hash).toBe('#top')
    },
  )

  it('writes the chosen day to the URL without adding a history entry', () => {
    goTo('/?salles=champo')
    const push = vi.spyOn(window.history, 'pushState')
    const { result } = renderHook(() => useSelectedDay())
    act(() => result.current.setDay('2026-11-25'))
    expect(result.current.day).toBe('2026-11-25')
    expect(window.location.search).toBe('?salles=champo&jour=2026-11-25')
    // Today is written too: a shared link names a date.
    act(() => result.current.setDay('2026-11-23'))
    expect(window.location.search).toBe('?salles=champo&jour=2026-11-23')
    expect(push).not.toHaveBeenCalled()
  })

  it('follows the URL on popstate', () => {
    const { result } = renderHook(() => useSelectedDay())
    act(() => {
      goTo('/?jour=2026-11-26')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    expect(result.current.day).toBe('2026-11-26')
  })

  it('moves today at Paris midnight and drops a day that left the window', () => {
    goTo('/?jour=2026-11-23')
    const { result } = renderHook(() => useSelectedDay())
    // Paris midnight is 23:00 UTC in winter, 13 h after NOW.
    act(() => vi.advanceTimersByTime(13 * 3_600_000 - 1_000))
    expect(result.current.today).toBe('2026-11-23')
    act(() => vi.advanceTimersByTime(3_000))
    expect(result.current.today).toBe('2026-11-24')
    expect(result.current.week[6]).toBe('2026-11-30')
    expect(result.current.day).toBe('2026-11-24')
    expect(window.location.search).toBe('')
  })

  it('re-arms the midnight timer when it fires early', () => {
    const setTimer = vi.spyOn(window, 'setTimeout')
    const { result } = renderHook(() => useSelectedDay())
    expect(setTimer).toHaveBeenCalledTimes(1)
    const [atMidnight, delay] = setTimer.mock.calls[0]
    // 00:00:01 Paris = 23:00:01 UTC, 13 h after NOW.
    expect(delay).toBe(13 * 3_600_000 + 1_000)
    // Fired while Paris is still on the 23rd: no re-render, so it must re-arm itself.
    act(() => (atMidnight as () => void)())
    expect(result.current.today).toBe('2026-11-23')
    expect(setTimer).toHaveBeenCalledTimes(2)
  })

  it('keeps a day still in the window after midnight', () => {
    goTo('/?jour=2026-11-26')
    const { result } = renderHook(() => useSelectedDay())
    act(() => vi.advanceTimersByTime(24 * 3_600_000))
    expect(result.current.today).toBe('2026-11-24')
    expect(result.current.day).toBe('2026-11-26')
    expect(window.location.search).toBe('?jour=2026-11-26')
  })

  it('catches up on today when the tab becomes visible again', () => {
    const { result } = renderHook(() => useSelectedDay())
    // A sleeping phone: the clock jumps without the timer firing.
    vi.setSystemTime(new Date('2026-11-25T08:00:00Z'))
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    expect(result.current.today).toBe('2026-11-25')
    expect(result.current.day).toBe('2026-11-25')
  })
})
