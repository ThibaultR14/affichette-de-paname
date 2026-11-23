import { parisDate } from './days'

/** What the import knows about a cinema's programme (columns of `cinemas`). */
export type Coverage = {
  /** Paris date (YYYY-MM-DD) of the last imported screening. */
  coverageUntil: string | null
  /** Last successful import (ISO instant). */
  lastSuccessAt: string | null
  /** Outcome of the latest import, null if the cinema was never imported. */
  lastImportOk: boolean | null
}

export type CoverageStatus = { line: string | null; failed: boolean }

const weekdayShort = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', timeZone: 'UTC' })
const monthShort = new Intl.DateTimeFormat('fr-FR', { month: 'short', timeZone: 'UTC' })

function utcDay(day: string): Date {
  const [y, m, d] = day.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d))
}

/**
 * « jeu. 27 » within 6 days of `today`, « 16 nov. » beyond (a weekday alone would be
 * ambiguous for a coverage several weeks old). Both are Paris dates (YYYY-MM-DD).
 */
export function coverageDate(day: string, today: string): string {
  const date = utcDay(day)
  const offset = Math.round((date.getTime() - utcDay(today).getTime()) / 86_400_000)
  const d = date.getUTCDate()
  if (Math.abs(offset) <= 6) return `${weekdayShort.format(date)} ${d}`
  return `${d} ${monthShort.format(date)}`
}

/** « à l’instant », « il y a 12 min », « il y a 3 h », « il y a 2 j » (rounded down). */
export function timeAgo(instant: Date, now: Date): string {
  const minutes = Math.floor((now.getTime() - instant.getTime()) / 60_000)
  if (minutes < 1) return 'à l’instant'
  if (minutes < 60) return `il y a ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `il y a ${hours} h`
  return `il y a ${Math.floor(hours / 24)} j`
}

/** The muted line under a cinema, and whether to say its latest import failed. */
export function coverageStatus(
  coverage: Coverage,
  today: string = parisDate(new Date()),
  now: Date = new Date(),
): CoverageStatus {
  const failed = coverage.lastImportOk === false
  const parts: string[] = []
  if (coverage.coverageUntil) {
    parts.push(`programme connu jusqu’au ${coverageDate(coverage.coverageUntil, today)}`)
  }
  if (coverage.lastSuccessAt) {
    parts.push(`mis à jour ${timeAgo(new Date(coverage.lastSuccessAt), now)}`)
  }
  if (parts.length) return { line: parts.join(' · '), failed }
  return { line: failed ? null : 'pas encore de programme pour cette salle', failed }
}
