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

/** The 7 Paris calendar days of the rolling window, today first. */
export function rollingWeek(now: Date): string[] {
  const [y, m, d] = parisDate(now).split('-').map(Number)
  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(Date.UTC(y, m - 1, d + i))
    return day.toISOString().slice(0, 10)
  })
}
