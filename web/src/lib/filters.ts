import { useCallback, useEffect, useState } from 'react'
import type { DayFilm } from './screenings'
import { replaceSearch } from './url'

/** Filters of the day view, kept in the URL (`?salles=champo,louxor&ugc=1&patrimoine=0`). */
export type Filters = {
  /** Cinema ids, sorted; empty = every cinema. */
  cinemas: string[]
  /** Only cinemas taking the UGC Illimité card. */
  ugc: boolean
  /** Only films released 20+ years ago (films without a known year stay visible). */
  heritage: boolean
}

/** What a bare URL means: heritage is on by default. */
export const DEFAULT_FILTERS: Filters = { cinemas: [], ugc: false, heritage: true }

/** Everything shown (« tout effacer »). */
export const NO_FILTERS: Filters = { cinemas: [], ugc: false, heritage: false }

const CINEMAS = 'salles'
const UGC = 'ugc'
const HERITAGE = 'patrimoine'
const CINEMA_ID = /^[a-z0-9-]+$/
const HERITAGE_AGE = 20

function sortedIds(ids: string[]): string[] {
  return [...new Set(ids)].sort()
}

export function readFilters(search: string): Filters {
  const params = new URLSearchParams(search)
  const ids = (params.get(CINEMAS) ?? '')
    .split(',')
    .map((id) => id.trim())
    .filter((id) => CINEMA_ID.test(id))
  return {
    cinemas: sortedIds(ids),
    ugc: params.get(UGC) === '1',
    heritage: params.get(HERITAGE) !== '0',
  }
}

/** `search` with the filters written (defaults left out), other parameters kept. */
export function withFilters(search: string, filters: Filters): string {
  const params = new URLSearchParams(search)
  if (filters.cinemas.length) params.set(CINEMAS, sortedIds(filters.cinemas).join(','))
  else params.delete(CINEMAS)
  if (filters.ugc) params.set(UGC, '1')
  else params.delete(UGC)
  if (filters.heritage) params.delete(HERITAGE)
  else params.set(HERITAGE, '0')
  // Commas stay readable in a shared link (`salles=champo,louxor`), ids never contain one.
  const query = params.toString().replaceAll('%2C', ',')
  return query ? `?${query}` : ''
}

export function hasActiveFilters(filters: Filters): boolean {
  return filters.cinemas.length > 0 || filters.ugc || filters.heritage
}

/** Latest release year still counted as heritage, from the Paris day `today` (YYYY-MM-DD). */
export function heritageMaxYear(today: string): number {
  return Number(today.slice(0, 4)) - HERITAGE_AGE
}

/**
 * Cards passing the filters. Cinemas filters remove the cinemas that do not pass from each card,
 * then the cards left without a cinema. Heritage keeps films without a known year.
 */
export function filterFilms(films: DayFilm[], filters: Filters, today: string): DayFilm[] {
  const maxYear = heritageMaxYear(today)
  const chosen = new Set(filters.cinemas)
  const byCinema = chosen.size > 0 || filters.ugc

  return films.flatMap((film) => {
    if (filters.heritage && film.year != null && film.year > maxYear) return []
    if (!byCinema) return [film]
    const cinemas = film.cinemas.filter(
      (c) => (chosen.size === 0 || chosen.has(c.cinemaId)) && (!filters.ugc || c.acceptsUgc),
    )
    return cinemas.length ? [{ ...film, cinemas }] : []
  })
}

/** Filters read from `window.location`, written with `replaceState` like the day. */
export function useFilters() {
  const [filters, setState] = useState(() => readFilters(window.location.search))

  // Malformed values (`?salles=Champo`, `?ugc=oui`) are ignored: the URL is rewritten to say so.
  useEffect(() => {
    const { search } = window.location
    const clean = withFilters(search, readFilters(search))
    if (clean !== search) replaceSearch(clean)
  }, [])

  useEffect(() => {
    const onPop = () => setState(readFilters(window.location.search))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const setFilters = useCallback((next: Filters) => {
    const clean = { ...next, cinemas: sortedIds(next.cinemas) }
    replaceSearch(withFilters(window.location.search, clean))
    setState(clean)
  }, [])

  return { filters, setFilters }
}
