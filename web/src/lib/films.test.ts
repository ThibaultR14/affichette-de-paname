import { describe, expect, it, vi } from 'vitest'
import { fetchFilm, fetchFilmScreenings, groupByDay, type FilmScreeningRow } from './films'
import { MAX_ROWS, type ScreeningsClient } from './screenings'

function fakeClient(result: { data: unknown; error: { message: string } | null }) {
  const chain = () => vi.fn((..._args: unknown[]) => builder)
  const builder = {
    select: chain(),
    eq: chain(),
    gte: chain(),
    lt: chain(),
    is: chain(),
    order: chain(),
    limit: vi.fn((..._args: unknown[]) => Promise.resolve(result)),
    maybeSingle: vi.fn(() => Promise.resolve(result)),
  }
  const from = vi.fn((..._args: unknown[]) => builder)
  return { client: { from } as unknown as ScreeningsClient, from, ...builder }
}

const mepris = {
  tmdb_id: 266,
  title: 'Le Mépris',
  original_title: 'Le Mépris',
  year: 1963,
  runtime_min: 103,
  directors: ['Jean-Luc Godard'],
  overview: 'Paul, scénariste…',
  poster_path: '/mepris.jpg',
}

describe('fetchFilm', () => {
  it('reads one film by TMDB id', async () => {
    const fake = fakeClient({ data: mepris, error: null })
    await expect(fetchFilm(266, { client: fake.client })).resolves.toEqual({
      tmdbId: 266,
      title: 'Le Mépris',
      originalTitle: 'Le Mépris',
      year: 1963,
      runtimeMin: 103,
      directors: ['Jean-Luc Godard'],
      overview: 'Paul, scénariste…',
      posterUrl: 'https://image.tmdb.org/t/p/w500/mepris.jpg',
    })
    expect(fake.from).toHaveBeenCalledWith('films')
    expect(fake.select.mock.calls[0][0]).toMatch(/original_title.*overview/)
    expect(fake.eq).toHaveBeenCalledWith('tmdb_id', 266)
  })

  it('returns null for a film that is not in the base', async () => {
    const fake = fakeClient({ data: null, error: null })
    await expect(fetchFilm(1, { client: fake.client })).resolves.toBeNull()
  })

  it('has no poster url without a poster', async () => {
    const fake = fakeClient({ data: { ...mepris, poster_path: null }, error: null })
    expect((await fetchFilm(266, { client: fake.client }))?.posterUrl).toBeNull()
  })

  it('throws on a Supabase error, or without Supabase', async () => {
    const fake = fakeClient({ data: null, error: { message: 'boom' } })
    await expect(fetchFilm(266, { client: fake.client })).rejects.toThrow('boom')
    await expect(fetchFilm(266, { client: null })).rejects.toThrow(/VITE_SUPABASE_URL/)
  })
})

const champo = { id: 'champo', name: 'Le Champo', accepts_ugc: true, website_url: 'https://champo' }
const louxor = { id: 'louxor', name: 'Le Louxor', accepts_ugc: true, website_url: null }

function row(over: Partial<FilmScreeningRow>): FilmScreeningRow {
  return {
    source_key: 'k',
    starts_at: '2026-11-24T13:00:00+00:00',
    version: null,
    format: null,
    booking_url: null,
    cinema: champo,
    ...over,
  }
}

describe('fetchFilmScreenings', () => {
  const now = new Date('2026-11-24T15:30:00Z') // tuesday 16:30 in Paris

  it('reads the film’s non-cancelled screenings from now to the end of the 7 days', async () => {
    const rows = [row({})]
    const fake = fakeClient({ data: rows, error: null })
    await expect(fetchFilmScreenings(266, { now, client: fake.client })).resolves.toEqual(rows)
    expect(fake.from).toHaveBeenCalledWith('screenings')
    expect(fake.select.mock.calls[0][0]).toMatch(/cinema:cinemas\(.*website_url.*\)/)
    expect(fake.eq).toHaveBeenCalledWith('tmdb_id', 266)
    expect(fake.gte).toHaveBeenCalledWith('starts_at', '2026-11-24T15:30:00.000Z')
    // monday 30 at midnight in Paris
    expect(fake.lt).toHaveBeenCalledWith('starts_at', '2026-11-30T23:00:00.000Z')
    expect(fake.is).toHaveBeenCalledWith('cancelled_at', null)
    expect(fake.order).toHaveBeenCalledWith('starts_at')
    expect(fake.limit).toHaveBeenCalledWith(MAX_ROWS)
  })

  it('throws on a Supabase error, without Supabase, and on a truncated week', async () => {
    const error = fakeClient({ data: null, error: { message: 'boom' } })
    await expect(fetchFilmScreenings(266, { now, client: error.client })).rejects.toThrow('boom')
    await expect(fetchFilmScreenings(266, { now, client: null })).rejects.toThrow(
      /VITE_SUPABASE_URL/,
    )
    const full = fakeClient({ data: Array.from({ length: MAX_ROWS }, () => row({})), error: null })
    await expect(fetchFilmScreenings(266, { now, client: full.client })).rejects.toThrow(/1000/)
  })
})

describe('groupByDay', () => {
  it('groups by Paris day, then by cinema', () => {
    const days = groupByDay([
      row({ source_key: 'a', starts_at: '2026-11-24T19:00:00Z', cinema: louxor }),
      row({ source_key: 'b', starts_at: '2026-11-24T13:00:00Z' }),
      // 00:30 in Paris on wednesday 26, still the 25th in UTC
      row({ source_key: 'c', starts_at: '2026-11-25T23:30:00Z' }),
      row({ source_key: 'd', starts_at: '2026-11-25T18:00:00Z', booking_url: 'https://resa/d' }),
    ])
    expect(days.map((d) => d.day)).toEqual(['2026-11-24', '2026-11-25', '2026-11-26'])
    expect(days[0].cinemas.map((c) => c.cinemaName)).toEqual(['Le Champo', 'Le Louxor'])
    expect(days[1].cinemas[0].showtimes[0]).toMatchObject({ id: 'd', bookingUrl: 'https://resa/d' })
    expect(days[2].cinemas[0].showtimes[0]).toMatchObject({ id: 'c', bookingUrl: 'https://champo' })
  })

  it('is empty without screenings', () => {
    expect(groupByDay([])).toEqual([])
  })
})
