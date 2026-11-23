import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { DayFilm } from '../lib/screenings'
import { DayScreenings } from './DayScreenings'

const mepris: DayFilm = {
  key: 'tmdb:266',
  tmdbId: 266,
  title: 'Le Mépris',
  directors: ['Jean-Luc Godard'],
  year: 1963,
  runtimeMin: 103,
  posterUrl: 'https://image.tmdb.org/t/p/w342/mepris.jpg',
  tilt: 1,
  cinemas: [
    {
      cinemaId: 'champo',
      cinemaName: 'Le Champo',
      acceptsUgc: true,
      showtimes: [
        {
          id: 'scare:champo:1',
          startsAt: '2026-11-24T13:00:00Z',
          version: 'VO',
          format: '35mm',
          bookingUrl: 'https://resa/1',
        },
      ],
    },
  ],
}

const unmatched: DayFilm = {
  key: 'raw:nuit des courts',
  tmdbId: null,
  title: 'Nuit des courts',
  posterUrl: null,
  cinemas: [
    {
      cinemaId: 'louxor',
      cinemaName: 'Le Louxor',
      acceptsUgc: true,
      showtimes: [{ id: 'x', startsAt: '2026-11-24T20:00:00Z', bookingUrl: null }],
    },
  ],
}

const today = '2026-11-24'

describe('DayScreenings', () => {
  it('says it is loading first', () => {
    render(<DayScreenings day={today} today={today} load={() => new Promise(() => {})} />)
    expect(screen.getByText('on déplie l’affichette…')).toBeInTheDocument()
  })

  it('shows one card per film with its showtimes', async () => {
    render(
      <DayScreenings day={today} today={today} load={() => Promise.resolve([mepris, unmatched])} />,
    )
    expect(await screen.findByRole('heading', { name: '2 films aujourd’hui' })).toBeInTheDocument()
    const card = screen.getByRole('heading', { name: 'Le Mépris' }).closest('article')!
    expect(within(card).getByText('Jean-Luc Godard, 1963 · 1 h 43')).toBeInTheDocument()
    const link = within(card).getByRole('link', { name: /14:00 → 15:43/ })
    expect(link).toHaveAttribute('href', 'https://resa/1')
    expect(link).toHaveTextContent('vo')
    expect(link).toHaveTextContent('35mm')
  })

  it('shows an unmatched screening with the cinema title', async () => {
    render(<DayScreenings day={today} today={today} load={() => Promise.resolve([unmatched])} />)
    expect(await screen.findByRole('heading', { name: '1 film aujourd’hui' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Nuit des courts' })).toBeInTheDocument()
    expect(screen.getByText("(on n'a pas trouvé ce film, désolé)")).toBeInTheDocument()
  })

  it('says so when nothing is on that day', async () => {
    render(<DayScreenings day="2026-11-26" today={today} load={() => Promise.resolve([])} />)
    expect(
      await screen.findByText('rien de programmé jeudi 26 pour l’instant.'),
    ).toBeInTheDocument()
  })

  it('apologises when the database cannot be reached', async () => {
    render(
      <DayScreenings day={today} today={today} load={() => Promise.reject(new Error('offline'))} />,
    )
    expect(
      await screen.findByText('(on n’arrive pas à joindre la base, réessaie plus tard)'),
    ).toBeInTheDocument()
  })

  it('reloads when the day changes and ignores a late answer for the old day', async () => {
    let resolveOld: (films: DayFilm[]) => void = () => {}
    const load = vi.fn((day: string) =>
      day === today
        ? new Promise<DayFilm[]>((r) => (resolveOld = r))
        : Promise.resolve([unmatched]),
    )
    const { rerender } = render(<DayScreenings day={today} today={today} load={load} />)
    rerender(<DayScreenings day="2026-11-26" today={today} load={load} />)
    expect(await screen.findByRole('heading', { name: '1 film jeudi 26' })).toBeInTheDocument()
    resolveOld([mepris, unmatched])
    await Promise.resolve()
    expect(screen.getByRole('heading', { name: '1 film jeudi 26' })).toBeInTheDocument()
    expect(load).toHaveBeenCalledTimes(2)
  })
})
