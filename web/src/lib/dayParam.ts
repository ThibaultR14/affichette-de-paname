import { useCallback, useEffect, useMemo, useState } from 'react'
import { parisDate, parisDayRange, resolveDay, weekStarting } from './days'
import { replaceSearch } from './url'

const PARAM = 'jour'

/** Raw `?jour=` value of a query string, or null. */
export function readDayParam(search: string): string | null {
  return new URLSearchParams(search).get(PARAM)
}

/** `search` with `jour` set to `day` (or removed when null), other parameters kept. */
export function withDayParam(search: string, day: string | null): string {
  const params = new URLSearchParams(search)
  if (day === null) params.delete(PARAM)
  else params.set(PARAM, day)
  const query = params.toString()
  return query ? `?${query}` : ''
}

/** Small delay past midnight, so the timer never fires on the old day. */
const MIDNIGHT_MARGIN_MS = 1_000

/**
 * Selected day of the 7-day window, kept in `?jour=`.
 * Missing, malformed or out-of-window values mean today and are removed from the URL.
 * `today` moves at Paris midnight and when the tab becomes visible again.
 */
export function useSelectedDay() {
  const [today, setToday] = useState(() => parisDate(new Date()))
  const [param, setParam] = useState(() => readDayParam(window.location.search))

  const week = useMemo(() => weekStarting(today), [today])
  const day = resolveDay(param, week)

  // An invalid ?jour= (or one that left the window at midnight) is dropped from the URL.
  // `day` already falls back to today, so only the URL needs syncing.
  useEffect(() => {
    if (param !== null && param !== day && readDayParam(window.location.search) !== null) {
      replaceSearch(withDayParam(window.location.search, null))
    }
  }, [param, day])

  useEffect(() => {
    const refresh = () => setToday(parisDate(new Date()))
    let timer = 0
    const arm = () => {
      const delay = Date.parse(parisDayRange(today).to) - Date.now() + MIDNIGHT_MARGIN_MS
      timer = window.setTimeout(atMidnight, Math.max(delay, MIDNIGHT_MARGIN_MS))
    }
    // A timer that fires early (same day, so no re-render) is re-armed instead of lost.
    const atMidnight = () => (parisDate(new Date()) === today ? arm() : refresh())
    arm()
    // Timers sleep with the phone: catch up when the tab comes back.
    document.addEventListener('visibilitychange', refresh)
    return () => {
      window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', refresh)
    }
  }, [today])

  useEffect(() => {
    const onPop = () => setParam(readDayParam(window.location.search))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const setDay = useCallback((next: string) => {
    replaceSearch(withDayParam(window.location.search, next))
    setParam(next)
  }, [])

  return { today, week, day, setDay }
}
