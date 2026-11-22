export const PARIS_TZ = 'Europe/Paris'

/** Calendar date (YYYY-MM-DD) of `instant` in Europe/Paris. */
export function parisDate(instant: Date): string {
  // en-CA formats as YYYY-MM-DD
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: PARIS_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(instant)
}

const timeFormat = new Intl.DateTimeFormat('fr-FR', {
  timeZone: PARIS_TZ,
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

/** Wall-clock time of `instant` in Paris, « 14:00 ». */
export function parisTime(instant: Date): string {
  return timeFormat.format(instant)
}

const NBSP = ' '

/** « 1 h 45 », « 2 h », « 52 min », with non-breaking spaces so a runtime never wraps. */
export function formatRuntime(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m}${NBSP}min`
  return m === 0 ? `${h}${NBSP}h` : `${h}${NBSP}h${NBSP}${String(m).padStart(2, '0')}`
}

const weekdayShort = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', timeZone: 'UTC' })

/**
 * Label of a day in the 7-day strip: « auj. », « dem. », then « mer. 25 ».
 * `day` and `today` are Paris calendar dates (YYYY-MM-DD).
 */
export function dayLabel(day: string, today: string): string {
  const [y, m, d] = day.split('-').map(Number)
  const date = new Date(Date.UTC(y, m - 1, d))
  const [ty, tm, td] = today.split('-').map(Number)
  const offset = Math.round((date.getTime() - Date.UTC(ty, tm - 1, td)) / 86_400_000)
  if (offset === 0) return 'auj.'
  if (offset === 1) return 'dem.'
  return `${weekdayShort.format(date)} ${d}`
}

/** The 7 Paris calendar days of the rolling window, today first. */
export function rollingWeek(now: Date): string[] {
  const [y, m, d] = parisDate(now).split('-').map(Number)
  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(Date.UTC(y, m - 1, d + i))
    return day.toISOString().slice(0, 10)
  })
}
