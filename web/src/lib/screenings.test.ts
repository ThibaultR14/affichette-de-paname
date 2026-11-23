import { describe, expect, it, vi } from 'vitest'
import {
  MAX_ROWS,
  fetchDayScreenings,
  groupByFilm,
  type ScreeningRow,
  type ScreeningsClient,
} from './screenings'

function fakeClient(result: { data: unknown; error: { message: string } | null }) {
  const chain = () => vi.fn((..._args: unknown[]) => builder)
  const builder = {
    select: chain(),
    gte: chain(),
    lt: chain(),
    is: chain(),
    order: chain(),
    limit: vi.fn((..._args: unknown[]) => Promise.resolve(result)),
  }
  const from = vi.fn((..._args: unknown[]) => builder)
  return { client: { from } as unknown as ScreeningsClient, from, ...builder }
}

const champo = { id: 'champo', name: 'Le Champo', accepts_ugc: true, website_url: 'https://champo' }
const louxor = { id: 'louxor', name: 'Le Louxor', accepts_ugc: true, website_url: null }
const etoile = {
  id: 'etoile',
  name: "Club de l'Étoile",
  accepts_ugc: false,
  website_url: 'https://etoile',
}
const mepris = {
  tmdb_id: 266,
  title: 'Le Mépris',
  year: 1963,
  runtime_min: 103,
  directors: ['Jean-Luc Godard'],
  poster_path: '/mepris.jpg',
}
const alphaville = { ...mepris, tmdb_id: 8072, title: 'Alphaville', poster_path: null }

function row(over: Partial<ScreeningRow>): ScreeningRow {
  return {
    source_key: 'k',
    raw_title: 'LE MEPRIS',
    starts_at: '2026-11-24T13:00:00+00:00',
    version: null,
    format: null,
    booking_url: null,
    cinema: champo,
    film: mepris,
    ...over,
  }
}

describe('fetchDayScreenings', () => {
  const now = new Date('2026-11-24T15:30:00Z') // 16:30 in Paris

  it('reads the non-cancelled screenings of a Paris day, by start time', async () => {
    const rows = [row({})]
    const fake = fakeClient({ data: rows, error: null })
    await expect(fetchDayScreenings('2026-11-25', { now, client: fake.client })).resolves.toEqual(
      rows,
    )
    expect(fake.from).toHaveBeenCalledWith('screenings')
    expect(fake.select.mock.calls[0][0]).toMatch(/cinema:cinemas\(.*website_url.*\)/)
    expect(fake.select.mock.calls[0][0]).toMatch(/film:films\(.*poster_path.*\)/)
    expect(fake.gte).toHaveBeenCalledWith('starts_at', '2026-11-24T23:00:00.000Z')
    expect(fake.lt).toHaveBeenCalledWith('starts_at', '2026-11-25T23:00:00.000Z')
    expect(fake.is).toHaveBeenCalledWith('cancelled_at', null)
    expect(fake.order).toHaveBeenCalledWith('starts_at')
    expect(fake.limit).toHaveBeenCalledWith(MAX_ROWS)
  })

  it('skips the screenings that already started today', async () => {
    const fake = fakeClient({ data: [], error: null })
    await fetchDayScreenings('2026-11-24', { now, client: fake.client })
    expect(fake.gte).toHaveBeenCalledWith('starts_at', '2026-11-24T15:30:00.000Z')
    expect(fake.lt).toHaveBeenCalledWith('starts_at', '2026-11-24T23:00:00.000Z')
  })

  it('throws when Supabase returns an error', async () => {
    const fake = fakeClient({ data: null, error: { message: 'boom' } })
    await expect(fetchDayScreenings('2026-11-24', { now, client: fake.client })).rejects.toThrow(
      'boom',
    )
  })

  it('throws a clear error when Supabase is not configured', async () => {
    await expect(fetchDayScreenings('2026-11-24', { now, client: null })).rejects.toThrow(
      /VITE_SUPABASE_URL/,
    )
  })

  it('refuses a truncated day', async () => {
    const fake = fakeClient({ data: Array.from({ length: MAX_ROWS }, () => row({})), error: null })
    await expect(fetchDayScreenings('2026-11-24', { now, client: fake.client })).rejects.toThrow(
      /1000/,
    )
  })
})

describe('groupByFilm', () => {
  it('makes one card per film, cinemas by name, showtimes by time', () => {
    const films = groupByFilm([
      row({ source_key: 'a', cinema: louxor, starts_at: '2026-11-24T12:00:00+00:00' }),
      row({ source_key: 'b', cinema: champo, starts_at: '2026-11-24T19:00:00+00:00' }),
      row({ source_key: 'c', cinema: champo, starts_at: '2026-11-24T13:00:00+00:00' }),
      row({ source_key: 'd', film: alphaville, raw_title: 'ALPHAVILLE' }),
    ])
    expect(films.map((f) => f.title)).toEqual(['Alphaville', 'Le Mépris'])
    const card = films[1]
    expect(card).toMatchObject({
      tmdbId: 266,
      directors: ['Jean-Luc Godard'],
      year: 1963,
      runtimeMin: 103,
      posterUrl: 'https://image.tmdb.org/t/p/w342/mepris.jpg',
    })
    expect(card.cinemas.map((c) => c.cinemaName)).toEqual(['Le Champo', 'Le Louxor'])
    expect(card.cinemas[0].showtimes.map((s) => s.id)).toEqual(['c', 'b'])
    expect(films[0].posterUrl).toBeNull()
  })

  it('keeps the cinema title of a screening without TMDB match', () => {
    const [card] = groupByFilm([row({ film: null, raw_title: 'Nuit des courts' })])
    expect(card).toMatchObject({ tmdbId: null, title: 'Nuit des courts', posterUrl: null })
  })

  it('groups unmatched screenings that share a title, across cinemas', () => {
    const films = groupByFilm([
      row({ source_key: 'a', film: null, raw_title: 'Nuit des courts' }),
      row({ source_key: 'b', film: null, raw_title: ' NUIT  des courts', cinema: louxor }),
      row({ source_key: 'c', film: null, raw_title: 'Autre chose' }),
    ])
    expect(films).toHaveLength(2)
    const nuit = films.find((f) => f.title === 'Nuit des courts')!
    expect(nuit.cinemas).toHaveLength(2)
  })

  it('does not merge an unmatched title with a matched film', () => {
    const films = groupByFilm([row({ source_key: 'a' }), row({ source_key: 'b', film: null })])
    expect(films).toHaveLength(2)
  })

  it('links to the booking page, else the cinema programme, else nothing', () => {
    const [card] = groupByFilm([
      row({ source_key: 'a', booking_url: 'https://resa/1' }),
      row({ source_key: 'b', starts_at: '2026-11-24T14:00:00+00:00' }),
      row({ source_key: 'c', cinema: louxor }),
    ])
    const urls = card.cinemas.flatMap((c) => c.showtimes.map((s) => s.bookingUrl))
    expect(urls).toEqual(['https://resa/1', 'https://champo', null])
  })

  it('carries version, format and the ugc flag', () => {
    const [card] = groupByFilm([row({ version: 'VO', format: '35mm', cinema: etoile })])
    expect(card.cinemas[0]).toMatchObject({ acceptsUgc: false, cinemaId: 'etoile' })
    expect(card.cinemas[0].showtimes[0]).toMatchObject({ version: 'VO', format: '35mm' })
  })

  it('gives each card a stable tilt within ±1.8°', () => {
    const rows = [row({}), row({ source_key: 'd', film: alphaville })]
    const first = groupByFilm(rows).map((f) => f.tilt)
    expect(groupByFilm(rows).map((f) => f.tilt)).toEqual(first)
    for (const t of first) expect(Math.abs(t!)).toBeLessThanOrEqual(1.8)
  })
})
