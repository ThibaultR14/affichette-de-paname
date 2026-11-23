import type { SupabaseClient } from '@supabase/supabase-js'
import type { CinemaShowtimes, FilmCardProps } from '../components/FilmCard'
import { parisDayRange } from './days'
import { supabase } from './supabase'

export type ScreeningsClient = Pick<SupabaseClient, 'from'>

/** A screening of the day, with its cinema and its TMDB film (null when unmatched). */
export type ScreeningRow = {
  source_key: string
  raw_title: string
  starts_at: string
  version: string | null
  format: string | null
  booking_url: string | null
  cinema: { id: string; name: string; accepts_ugc: boolean; website_url: string | null }
  film: {
    tmdb_id: number
    title: string
    year: number | null
    runtime_min: number | null
    directors: string[]
    poster_path: string | null
  } | null
}

/** One film card of the day view. */
export type DayFilm = FilmCardProps & { key: string }

/** PostgREST `max_rows` on Supabase: a full page means the day may be truncated. */
export const MAX_ROWS = 1000

const POSTER_BASE = 'https://image.tmdb.org/t/p/w342'
const MAX_TILT = 1.8

const SELECT = [
  'source_key, raw_title, starts_at, version, format, booking_url',
  'cinema:cinemas(id, name, accepts_ugc, website_url)',
  'film:films(tmdb_id, title, year, runtime_min, directors, poster_path)',
].join(', ')

/**
 * Non-cancelled screenings of a Paris calendar day, by start time. Screenings that already
 * started (`now`) are left out, which only matters for today.
 */
export async function fetchDayScreenings(
  day: string,
  { now = new Date(), client = supabase }: { now?: Date; client?: ScreeningsClient | null } = {},
): Promise<ScreeningRow[]> {
  if (!client) {
    throw new Error('Supabase is not configured (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY)')
  }
  const range = parisDayRange(day)
  const from = new Date(Math.max(now.getTime(), new Date(range.from).getTime())).toISOString()
  const { data, error } = await client
    .from('screenings')
    .select(SELECT)
    .gte('starts_at', from)
    .lt('starts_at', range.to)
    .is('cancelled_at', null)
    .order('starts_at')
    .limit(MAX_ROWS)
  if (error) throw new Error(error.message)
  const rows = data as unknown as ScreeningRow[]
  // The server caps a response at MAX_ROWS: a full page may hide more rows, so it counts as truncated.
  if (rows.length >= MAX_ROWS) {
    throw new Error(`more than ${MAX_ROWS} screenings on ${day}: the day would be truncated`)
  }
  return rows
}

function titleKey(title: string): string {
  return title.trim().replace(/\s+/g, ' ').toLocaleLowerCase('fr')
}

/** Stable tilt in [-1.8°, 1.8°] derived from the card key, so cards do not move on re-render. */
function tiltFor(key: string): number {
  let h = 0
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return Math.round((((h % 37) - 18) / 18) * MAX_TILT * 10) / 10
}

const byName = (a: string, b: string) => a.localeCompare(b, 'fr', { sensitivity: 'base' })

/** The fields of a screening that a showtime list needs. */
export type ShowtimeRow = Pick<
  ScreeningRow,
  'source_key' | 'starts_at' | 'version' | 'format' | 'booking_url' | 'cinema'
>

/**
 * Showtimes by cinema (cinemas by name, showtimes by time). A showtime links to its booking
 * page, else to the cinema programme, else nowhere.
 */
export function groupByCinema(rows: ShowtimeRow[]): CinemaShowtimes[] {
  const byCinema = new Map<string, CinemaShowtimes>()
  for (const r of rows) {
    let cinema = byCinema.get(r.cinema.id)
    if (!cinema) {
      cinema = {
        cinemaId: r.cinema.id,
        cinemaName: r.cinema.name,
        acceptsUgc: r.cinema.accepts_ugc,
        showtimes: [],
      }
      byCinema.set(r.cinema.id, cinema)
    }
    cinema.showtimes.push({
      id: r.source_key,
      startsAt: r.starts_at,
      version: r.version,
      format: r.format,
      bookingUrl: r.booking_url ?? r.cinema.website_url,
    })
  }
  return [...byCinema.values()]
    .sort((a, b) => byName(a.cinemaName, b.cinemaName))
    .map((c) => ({
      ...c,
      showtimes: [...c.showtimes].sort(
        (a, b) => new Date(a.startsAt).getTime() - new Date(b.startsAt).getTime(),
      ),
    }))
}

/** One card per film (TMDB id, else the cinema's title), cards by title. */
export function groupByFilm(rows: ScreeningRow[]): DayFilm[] {
  const byFilm = new Map<string, ScreeningRow[]>()
  for (const r of rows) {
    const key = r.film ? `tmdb:${r.film.tmdb_id}` : `raw:${titleKey(r.raw_title)}`
    const group = byFilm.get(key)
    if (group) group.push(r)
    else byFilm.set(key, [r])
  }

  return [...byFilm]
    .map(([key, group]): DayFilm => {
      const { film, raw_title } = group[0]
      return {
        key,
        tmdbId: film?.tmdb_id ?? null,
        title: film?.title ?? raw_title.trim(),
        directors: film?.directors ?? [],
        year: film?.year ?? null,
        runtimeMin: film?.runtime_min ?? null,
        posterUrl: film?.poster_path ? `${POSTER_BASE}${film.poster_path}` : null,
        cinemas: groupByCinema(group),
        tilt: tiltFor(key),
      }
    })
    .sort((a, b) => byName(a.title, b.title))
}
