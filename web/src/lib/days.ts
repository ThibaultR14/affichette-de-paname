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

/** The 7 calendar days starting on `first` (YYYY-MM-DD). */
export function weekStarting(first: string): string[] {
  const [y, m, d] = first.split('-').map(Number)
  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(Date.UTC(y, m - 1, d + i))
    return day.toISOString().slice(0, 10)
  })
}

/** The 7 Paris calendar days of the rolling window, today first. */
export function rollingWeek(now: Date): string[] {
  return weekStarting(parisDate(now))
}

/**
 * Day to show for a `?jour=` value: itself if it is one of `week`, otherwise today (`week[0]`).
 * Membership also rejects malformed values.
 */
export function resolveDay(param: string | null, week: string[]): string {
  return param !== null && week.includes(param) ? param : week[0]
}

const wallClock = new Intl.DateTimeFormat('en-US', {
  timeZone: PARIS_TZ,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: 'numeric',
  second: 'numeric',
  hourCycle: 'h23',
})

/** Offset of Paris from UTC at `instant`, in milliseconds (+1 h in winter, +2 h in summer). */
function parisOffset(instant: number): number {
  const parts = Object.fromEntries(
    wallClock.formatToParts(instant).map((p) => [p.type, Number(p.value)]),
  )
  const asUtc = Date.UTC(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour,
    parts.minute,
    parts.second,
  )
  return asUtc - Math.floor(instant / 1000) * 1000
}

/** UTC instant of 00:00 in Paris on `day` (YYYY-MM-DD). */
function parisMidnight(y: number, m: number, d: number): number {
  const wall = Date.UTC(y, m - 1, d)
  // Two passes: the offset at the guess may differ from the one at midnight around DST changes.
  const guess = wall - parisOffset(wall)
  return wall - parisOffset(guess)
}

/** `[from, to[` of a Paris calendar day as UTC ISO instants (23 h or 25 h on DST days). */
export function parisDayRange(day: string): { from: string; to: string } {
  const [y, m, d] = day.split('-').map(Number)
  return {
    from: new Date(parisMidnight(y, m, d)).toISOString(),
    to: new Date(parisMidnight(y, m, d + 1)).toISOString(),
  }
}

const weekdayLong = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', timeZone: 'UTC' })

/** Day in a sentence: « aujourd'hui », « demain », then « mercredi 25 ». */
export function dayTitle(day: string, today: string): string {
  const short = dayLabel(day, today)
  if (short === 'auj.') return 'aujourd’hui'
  if (short === 'dem.') return 'demain'
  const [y, m, d] = day.split('-').map(Number)
  return `${weekdayLong.format(new Date(Date.UTC(y, m - 1, d)))} ${d}`
}
