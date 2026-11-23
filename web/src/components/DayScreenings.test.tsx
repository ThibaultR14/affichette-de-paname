import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DEFAULT_FILTERS, NO_FILTERS } from '../lib/filters'
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

  describe('with filters', () => {
    const recent: DayFilm = { ...mepris, key: 'tmdb:1', tmdbId: 1, title: 'Anatomie', year: 2023 }

    it('applies them to the loaded day, without reloading', async () => {
      const load = vi.fn(() => Promise.resolve([mepris, recent, unmatched]))
      const { rerender } = render(
        <DayScreenings day={today} today={today} filters={NO_FILTERS} load={load} />,
      )
      expect(
        await screen.findByRole('heading', { name: '3 films aujourd’hui' }),
      ).toBeInTheDocument()
      rerender(<DayScreenings day={today} today={today} filters={DEFAULT_FILTERS} load={load} />)
      expect(screen.getByRole('heading', { name: '2 films aujourd’hui' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'Anatomie' })).not.toBeInTheDocument()
      rerender(
        <DayScreenings
          day={today}
          today={today}
          filters={{ ...NO_FILTERS, cinemas: ['louxor'] }}
          load={load}
        />,
      )
      expect(screen.getByRole('heading', { name: '1 film aujourd’hui' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'Nuit des courts' })).toBeInTheDocument()
      expect(load).toHaveBeenCalledTimes(1)
    })

    it('suggests dropping heritage when the filters leave nothing', async () => {
      const onClear = vi.fn()
      render(
        <DayScreenings
          day={today}
          today={today}
          filters={DEFAULT_FILTERS}
          onClearFilters={onClear}
          load={() => Promise.resolve([recent])}
        />,
      )
      expect(
        await screen.findByText('rien ce jour-là avec ces filtres. essaie sans « patrimoine » ?'),
      ).toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: 'tout effacer' }))
      expect(onClear).toHaveBeenCalledOnce()
    })

    it('does not mention heritage when it is off', async () => {
      render(
        <DayScreenings
          day={today}
          today={today}
          filters={{ ...NO_FILTERS, ugc: true }}
          load={() =>
            Promise.resolve([{ ...mepris, cinemas: [{ ...mepris.cinemas[0], acceptsUgc: false }] }])
          }
        />,
      )
      expect(await screen.findByText('rien ce jour-là avec ces filtres.')).toBeInTheDocument()
    })

    it('keeps the « nothing on » message for an empty day', async () => {
      render(
        <DayScreenings
          day={today}
          today={today}
          filters={DEFAULT_FILTERS}
          load={() => Promise.resolve([])}
        />,
      )
      expect(
        await screen.findByText('rien de programmé aujourd’hui pour l’instant.'),
      ).toBeInTheDocument()
    })
  })
})
