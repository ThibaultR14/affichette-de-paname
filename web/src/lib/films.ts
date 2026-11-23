import type { CinemaShowtimes } from '../components/FilmCard'
import { parisDate, parisDayRange, weekStarting } from './days'
import { MAX_ROWS, groupByCinema, type ScreeningsClient, type ShowtimeRow } from './screenings'
import { supabase } from './supabase'

/** A film of the `films` table, as shown on its page. */
export type Film = {
  tmdbId: number
  title: string
  originalTitle: string | null
  year: number | null
  runtimeMin: number | null
  directors: string[]
  overview: string | null
  posterUrl: string | null
}

type FilmRow = {
  tmdb_id: number
  title: string
  original_title: string | null
  year: number | null
  runtime_min: number | null
  directors: string[]
  overview: string | null
  poster_path: string | null
}

export type FilmScreeningRow = ShowtimeRow

/** The showtimes of one Paris day. */
export type FilmDay = { day: string; cinemas: CinemaShowtimes[] }

const POSTER_BASE = 'https://image.tmdb.org/t/p/w500'

type Options = { client?: ScreeningsClient | null }

function requireClient(client: ScreeningsClient | null | undefined): ScreeningsClient {
  if (!client) {
    throw new Error('Supabase is not configured (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY)')
  }
  return client
}

/** The film with this TMDB id, or null when the site has never met it. */
export async function fetchFilm(
  tmdbId: number,
  { client = supabase }: Options = {},
): Promise<Film | null> {
  const { data, error } = await requireClient(client)
    .from('films')
    .select('tmdb_id, title, original_title, year, runtime_min, directors, overview, poster_path')
    .eq('tmdb_id', tmdbId)
    .maybeSingle()
  if (error) throw new Error(error.message)
  if (!data) return null
  const f = data as FilmRow
  return {
    tmdbId: f.tmdb_id,
    title: f.title,
    originalTitle: f.original_title,
    year: f.year,
    runtimeMin: f.runtime_min,
    directors: f.directors ?? [],
    overview: f.overview,
    posterUrl: f.poster_path ? `${POSTER_BASE}${f.poster_path}` : null,
  }
}

/**
 * Non-cancelled screenings of a film over the 7-day window (today included), by start time,
 * from `now` on: screenings that already started are left out.
 */
export async function fetchFilmScreenings(
  tmdbId: number,
  { now = new Date(), client = supabase }: Options & { now?: Date } = {},
): Promise<FilmScreeningRow[]> {
  const week = weekStarting(parisDate(now))
  const start = parisDayRange(week[0]).from
  const from = new Date(Math.max(now.getTime(), new Date(start).getTime())).toISOString()
  const { data, error } = await requireClient(client)
    .from('screenings')
    .select(
      'source_key, starts_at, version, format, booking_url, cinema:cinemas(id, name, accepts_ugc, website_url)',
    )
    .eq('tmdb_id', tmdbId)
    .gte('starts_at', from)
    .lt('starts_at', parisDayRange(week[6]).to)
    .is('cancelled_at', null)
    .order('starts_at')
    .limit(MAX_ROWS)
  if (error) throw new Error(error.message)
  const rows = data as unknown as FilmScreeningRow[]
  if (rows.length >= MAX_ROWS) {
    throw new Error(
      `more than ${MAX_ROWS} screenings of film ${tmdbId}: the week would be truncated`,
    )
  }
  return rows
}

/** Showtimes by Paris day (in order), then by cinema. */
export function groupByDay(rows: FilmScreeningRow[]): FilmDay[] {
  const byDay = new Map<string, FilmScreeningRow[]>()
  for (const r of rows) {
    const day = parisDate(new Date(r.starts_at))
    const group = byDay.get(day)
    if (group) group.push(r)
    else byDay.set(day, [r])
  }
  return [...byDay]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, group]) => ({ day, cinemas: groupByCinema(group) }))
}
