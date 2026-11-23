import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { DayFilm } from './screenings'
import {
  DEFAULT_FILTERS,
  NO_FILTERS,
  filterFilms,
  hasActiveFilters,
  heritageMaxYear,
  readFilters,
  useFilters,
  withFilters,
} from './filters'

describe('readFilters', () => {
  it('defaults to every cinema, no ugc, heritage on', () => {
    expect(readFilters('')).toEqual({ cinemas: [], ugc: false, heritage: true })
    expect(readFilters('?jour=2026-11-24')).toEqual(DEFAULT_FILTERS)
  })

  it('reads the cinemas, sorted, deduplicated, malformed ids dropped', () => {
    expect(readFilters('?salles=louxor,champo').cinemas).toEqual(['champo', 'louxor'])
    expect(readFilters('?salles=champo,,champo, louxor ').cinemas).toEqual(['champo', 'louxor'])
    expect(readFilters('?salles=Champo,<x>,brady').cinemas).toEqual(['brady'])
    expect(readFilters('?salles=').cinemas).toEqual([])
  })

  it('turns ugc on only with ugc=1', () => {
    expect(readFilters('?ugc=1').ugc).toBe(true)
    expect(readFilters('?ugc=0').ugc).toBe(false)
    expect(readFilters('?ugc=oui').ugc).toBe(false)
  })

  it('turns heritage off only with patrimoine=0', () => {
    expect(readFilters('?patrimoine=0').heritage).toBe(false)
    expect(readFilters('?patrimoine=1').heritage).toBe(true)
    expect(readFilters('?patrimoine=non').heritage).toBe(true)
  })
})

describe('withFilters', () => {
  it('writes only what differs from the defaults and keeps jour', () => {
    expect(withFilters('?jour=2026-11-24', DEFAULT_FILTERS)).toBe('?jour=2026-11-24')
    expect(
      withFilters('?jour=2026-11-24', {
        cinemas: ['louxor', 'champo'],
        ugc: true,
        heritage: false,
      }),
    ).toBe('?jour=2026-11-24&salles=champo,louxor&ugc=1&patrimoine=0')
    expect(withFilters('?salles=champo&ugc=1&patrimoine=0&jour=2026-11-24', DEFAULT_FILTERS)).toBe(
      '?jour=2026-11-24',
    )
    expect(withFilters('', DEFAULT_FILTERS)).toBe('')
  })

  it('reads back what it writes', () => {
    const filters = { cinemas: ['brady', 'champo'], ugc: true, heritage: false }
    expect(readFilters(withFilters('', filters))).toEqual(filters)
  })
})

describe('hasActiveFilters', () => {
  it('is false only when nothing filters', () => {
    expect(hasActiveFilters(NO_FILTERS)).toBe(false)
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(true)
    expect(hasActiveFilters({ ...NO_FILTERS, ugc: true })).toBe(true)
    expect(hasActiveFilters({ ...NO_FILTERS, cinemas: ['champo'] })).toBe(true)
  })
})

function film(key: string, year: number | null, cinemas: [string, boolean][]): DayFilm {
  return {
    key,
    tmdbId: year === null ? null : Number(key.length),
    title: key,
    year,
    cinemas: cinemas.map(([cinemaId, acceptsUgc]) => ({
      cinemaId,
      cinemaName: cinemaId,
      acceptsUgc,
      showtimes: [{ id: `${key}:${cinemaId}`, startsAt: '2026-11-24T19:00:00Z', bookingUrl: null }],
    })),
  }
}

describe('filterFilms', () => {
  const today = '2026-11-24'
  const old = film('mepris', 1963, [
    ['champo', true],
    ['etoile', false],
  ])
  const recent = film('anatomie', 2023, [['louxor', true]])
  const unmatched = film('nuit des courts', null, [['etoile', false]])
  const films = [old, recent, unmatched]

  const keys = (list: DayFilm[]) => list.map((f) => f.key)
  const cinemaIds = (f: DayFilm) => f.cinemas.map((c) => c.cinemaId)

  it('keeps everything without filters', () => {
    expect(filterFilms(films, NO_FILTERS, today)).toEqual(films)
  })

  it('heritage threshold is the Paris year of today minus 20, inclusive', () => {
    expect(heritageMaxYear('2026-11-24')).toBe(2006)
    const edge = [film('a', 2006, [['champo', true]]), film('b', 2007, [['champo', true]])]
    expect(keys(filterFilms(edge, { ...NO_FILTERS, heritage: true }, today))).toEqual(['a'])
  })

  it('heritage keeps films without a known year', () => {
    const noYear = { ...film('x', 1990, [['champo', true]]), year: null }
    const result = filterFilms([...films, noYear], DEFAULT_FILTERS, today)
    expect(keys(result)).toEqual(['mepris', 'nuit des courts', 'x'])
  })

  it('keeps only the chosen cinemas and drops cards left without one', () => {
    const result = filterFilms(films, { ...NO_FILTERS, cinemas: ['etoile'] }, today)
    expect(keys(result)).toEqual(['mepris', 'nuit des courts'])
    expect(cinemaIds(result[0])).toEqual(['etoile'])
  })

  it('keeps only cinemas taking the ugc card', () => {
    const result = filterFilms(films, { ...NO_FILTERS, ugc: true }, today)
    expect(keys(result)).toEqual(['mepris', 'anatomie'])
    expect(cinemaIds(result[0])).toEqual(['champo'])
  })

  it('combines cinemas, ugc and heritage', () => {
    const result = filterFilms(
      films,
      { cinemas: ['etoile', 'louxor'], ugc: true, heritage: true },
      today,
    )
    expect(result).toEqual([])
    const ugcOnly = filterFilms(
      films,
      { cinemas: ['champo', 'louxor'], ugc: true, heritage: true },
      today,
    )
    expect(keys(ugcOnly)).toEqual(['mepris'])
  })
})

describe('useFilters', () => {
  beforeEach(() => window.history.replaceState(null, '', '/?jour=2026-11-24&salles=champo'))
  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState(null, '', '/')
  })

  it('reads the URL and writes changes with replaceState, keeping jour', () => {
    const push = vi.spyOn(window.history, 'pushState')
    const { result } = renderHook(() => useFilters())
    expect(result.current.filters).toEqual({ cinemas: ['champo'], ugc: false, heritage: true })
    act(() => result.current.setFilters({ cinemas: [], ugc: true, heritage: false }))
    expect(result.current.filters).toEqual({ cinemas: [], ugc: true, heritage: false })
    expect(window.location.search).toBe('?jour=2026-11-24&ugc=1&patrimoine=0')
    expect(push).not.toHaveBeenCalled()
  })

  it('removes malformed values from the URL and keeps the valid ones', () => {
    window.history.replaceState(null, '', '/?jour=2026-11-24&salles=Champo,louxor&ugc=oui')
    const { result } = renderHook(() => useFilters())
    expect(result.current.filters).toEqual({ cinemas: ['louxor'], ugc: false, heritage: true })
    expect(window.location.search).toBe('?jour=2026-11-24&salles=louxor')
  })

  it('leaves a clean URL alone', () => {
    const replace = vi.spyOn(window.history, 'replaceState')
    renderHook(() => useFilters())
    expect(replace).not.toHaveBeenCalled()
  })

  it('follows popstate', () => {
    const { result } = renderHook(() => useFilters())
    act(() => {
      window.history.replaceState(null, '', '/?ugc=1')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    expect(result.current.filters).toEqual({ cinemas: [], ugc: true, heritage: true })
  })
})
