import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Film, FilmDay } from '../lib/films'
import { navigate } from '../lib/router'
import { FilmPage, type FilmPageData } from './FilmPage'

const mepris: Film = {
  tmdbId: 266,
  title: 'Le Mépris',
  originalTitle: 'Le Mépris',
  year: 1963,
  runtimeMin: 103,
  directors: ['Jean-Luc Godard'],
  overview: 'Paul Javal, scénariste, accepte de récrire un film.',
  posterUrl: 'https://image.tmdb.org/t/p/w500/mepris.jpg',
}

const days: FilmDay[] = [
  {
    day: '2026-11-24',
    cinemas: [
      {
        cinemaId: 'champo',
        cinemaName: 'Le Champo',
        acceptsUgc: true,
        showtimes: [
          {
            id: 'a',
            startsAt: '2026-11-24T13:00:00Z',
            version: 'VO',
            format: '35mm',
            bookingUrl: 'https://resa/a',
          },
        ],
      },
    ],
  },
  {
    day: '2026-11-26',
    cinemas: [
      {
        cinemaId: 'louxor',
        cinemaName: 'Le Louxor',
        acceptsUgc: true,
        showtimes: [{ id: 'b', startsAt: '2026-11-26T19:30:00Z', bookingUrl: null }],
      },
    ],
  },
]

const today = '2026-11-24'
const loaded = (data: FilmPageData | null) => () => Promise.resolve(data)

afterEach(() => {
  window.history.replaceState(null, '', '/')
  vi.restoreAllMocks()
})

describe('FilmPage', () => {
  it('says it is loading first', () => {
    render(<FilmPage tmdbId={266} today={today} load={() => new Promise(() => {})} />)
    expect(screen.getByText('on déplie l’affichette…')).toBeInTheDocument()
  })

  it('shows the TMDB card of the film', async () => {
    const { container } = render(
      <FilmPage tmdbId={266} today={today} load={loaded({ film: mepris, days })} />,
    )
    expect(await screen.findByRole('heading', { level: 1, name: 'Le Mépris' })).toBeInTheDocument()
    expect(screen.getByText('Jean-Luc Godard, 1963 · 1 h 43')).toBeInTheDocument()
    expect(screen.getByText(mepris.overview!)).toBeInTheDocument()
    expect(container.querySelector('img')).toHaveAttribute('src', mepris.posterUrl)
    // same original title: not repeated
    expect(screen.queryByText(/titre original/)).not.toBeInTheDocument()
    expect(document.title).toBe('Le Mépris · l’affichette de paname')
  })

  it('gives the tab title back when leaving the page', async () => {
    document.title = 'L’Affichette de Paname'
    const { unmount } = render(
      <FilmPage tmdbId={266} today={today} load={loaded({ film: mepris, days })} />,
    )
    await screen.findByRole('heading', { level: 1, name: 'Le Mépris' })
    unmount()
    expect(document.title).toBe('L’Affichette de Paname')
  })

  it('shows the original title when it differs', async () => {
    const film = { ...mepris, title: 'La Mort aux trousses', originalTitle: 'North by Northwest' }
    render(<FilmPage tmdbId={213} today={today} load={loaded({ film, days })} />)
    expect(await screen.findByText('North by Northwest')).toBeInTheDocument()
  })

  it('lists the showtimes of the week, by day then cinema', async () => {
    render(<FilmPage tmdbId={266} today={today} load={loaded({ film: mepris, days })} />)
    const first = await screen.findByRole('region', { name: 'aujourd’hui' })
    const link = within(first).getByRole('link', { name: /14:00 → 15:43/ })
    expect(link).toHaveAttribute('href', 'https://resa/a')
    expect(link).toHaveTextContent('vo')
    expect(within(first).getByText('Le Champo')).toBeInTheDocument()
    const thursday = screen.getByRole('region', { name: 'jeudi 26' })
    expect(within(thursday).getByText('20:30')).toBeInTheDocument()
    expect(within(thursday).queryByRole('link')).toBeNull()
  })

  it('says so when the film is not showing this week', async () => {
    render(<FilmPage tmdbId={266} today={today} load={loaded({ film: mepris, days: [] })} />)
    expect(await screen.findByText('pas de séance dans les 7 prochains jours.')).toBeInTheDocument()
  })

  it('handles a film without poster, overview or meta', async () => {
    const bare: Film = {
      ...mepris,
      posterUrl: null,
      overview: null,
      directors: [],
      year: null,
      runtimeMin: null,
    }
    const { container } = render(
      <FilmPage tmdbId={266} today={today} load={loaded({ film: bare, days })} />,
    )
    expect(await screen.findByText('(pas de synopsis en français sur tmdb)')).toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('.film-page__poster--none')).not.toBeNull()
  })

  it('shows a clean 404 for a film the site does not know', async () => {
    render(<FilmPage tmdbId={999} today={today} load={loaded(null)} />)
    expect(
      await screen.findByRole('heading', { level: 1, name: 'film introuvable' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'retour à l’accueil' })).toHaveAttribute('href', '/')
  })

  it('says the base is out of reach on an error (not a 404)', async () => {
    render(<FilmPage tmdbId={266} today={today} load={() => Promise.reject(new Error('x'))} />)
    expect(
      await screen.findByText('(on n’arrive pas à joindre la base, réessaie plus tard)'),
    ).toBeInTheDocument()
    expect(screen.queryByText('film introuvable')).not.toBeInTheDocument()
  })

  it('goes back in history when the visitor came from the site', async () => {
    navigate('/film/266')
    const back = vi.spyOn(window.history, 'back').mockImplementation(() => {})
    render(<FilmPage tmdbId={266} today={today} load={loaded({ film: mepris, days })} />)
    fireEvent.click(await screen.findByRole('link', { name: '← toutes les séances' }))
    expect(back).toHaveBeenCalled()
  })

  it('goes to the home page from a shared link', async () => {
    window.history.replaceState(null, '', '/film/266')
    const back = vi.spyOn(window.history, 'back')
    render(<FilmPage tmdbId={266} today={today} load={loaded({ film: mepris, days })} />)
    const link = await screen.findByRole('link', { name: '← toutes les séances' })
    expect(link).toHaveAttribute('href', '/')
    fireEvent.click(link)
    expect(back).not.toHaveBeenCalled()
    expect(window.location.pathname).toBe('/')
  })
})
