import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./lib/cinemas', () => ({
  fetchCinemas: () =>
    Promise.resolve([
      { id: 'champo', name: 'Le Champo', arrondissement: 5, acceptsUgc: true },
      { id: 'etoile', name: "Club de l'Étoile", arrondissement: 17, acceptsUgc: false },
    ]),
}))

vi.mock('./lib/screenings', () => ({
  fetchDayScreenings: (day: string) => Promise.resolve([day]),
  groupByFilm: () => [
    {
      key: 'raw:nuit des courts',
      tmdbId: null,
      title: 'Nuit des courts',
      cinemas: [{ cinemaId: 'champo', cinemaName: 'Le Champo', acceptsUgc: true, showtimes: [] }],
    },
    {
      key: 'tmdb:1',
      tmdbId: 1,
      title: 'Anatomie',
      year: 2023,
      cinemas: [
        { cinemaId: 'etoile', cinemaName: "Club de l'Étoile", acceptsUgc: false, showtimes: [] },
      ],
    },
  ],
}))

describe('App', () => {
  beforeEach(() => {
    // Monday 23 Nov 2026 in Paris. Only Date is faked: the data promises must resolve.
    vi.useFakeTimers({ now: new Date('2026-11-23T10:00:00Z'), toFake: ['Date'] })
    window.history.replaceState(null, '', '/')
  })

  afterEach(() => {
    vi.useRealTimers()
    window.history.replaceState(null, '', '/')
  })

  function strip() {
    return within(screen.getByRole('navigation', { name: 'jours' }))
  }

  it('shows the site name', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent("l'affichette de paname")
  })

  it("shows today's films by default", async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: '1 film aujourd’hui' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Nuit des courts' })).toBeInTheDocument()
    expect(strip().getByRole('button', { name: 'auj.' })).toHaveAttribute('aria-current', 'date')
  })

  it('opens the day of a shared link', async () => {
    window.history.replaceState(null, '', '/?jour=2026-11-24')
    render(<App />)
    expect(await screen.findByRole('heading', { name: '1 film demain' })).toBeInTheDocument()
    expect(strip().getByRole('button', { name: 'dem.' })).toHaveAttribute('aria-current', 'date')
  })

  it('falls back to today for a date outside the window', async () => {
    window.history.replaceState(null, '', '/?jour=2026-12-25')
    render(<App />)
    expect(await screen.findByRole('heading', { name: '1 film aujourd’hui' })).toBeInTheDocument()
    expect(window.location.search).toBe('')
  })

  it('switches day from the strip and writes it to the URL', async () => {
    render(<App />)
    await screen.findByRole('heading', { name: '1 film aujourd’hui' })
    fireEvent.click(strip().getByRole('button', { name: 'mer. 25' }))
    expect(await screen.findByRole('heading', { name: '1 film mercredi 25' })).toBeInTheDocument()
    expect(window.location.search).toBe('?jour=2026-11-25')
    expect(strip().getByRole('button', { name: 'mer. 25' })).toHaveAttribute('aria-current', 'date')
  })

  it('lists the cinemas read from Supabase', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'les 2 salles' })).toBeInTheDocument()
  })

  describe('filters', () => {
    it('hides recent films by default (heritage on)', async () => {
      render(<App />)
      expect(await screen.findByRole('heading', { name: '1 film aujourd’hui' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'Anatomie' })).not.toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: 'retirer le filtre patrimoine' }),
      ).toBeInTheDocument()
    })

    it('applies the filters of a shared link and shows them as chips', async () => {
      window.history.replaceState(null, '', '/?jour=2026-11-24&salles=etoile&patrimoine=0')
      render(<App />)
      expect(await screen.findByRole('heading', { name: '1 film demain' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'Anatomie' })).toBeInTheDocument()
      expect(
        await screen.findByRole('button', { name: "retirer le filtre club de l'étoile" }),
      ).toBeInTheDocument()
    })

    it('writes a chip toggle to the URL, keeping the day', async () => {
      window.history.replaceState(null, '', '/?jour=2026-11-24')
      render(<App />)
      await screen.findByRole('heading', { name: '1 film demain' })
      fireEvent.click(screen.getByRole('button', { name: 'affiner' }))
      fireEvent.click(await screen.findByRole('button', { name: 'patrimoine (+ de 20 ans)' }))
      expect(window.location.search).toBe('?jour=2026-11-24&patrimoine=0')
      expect(screen.getByRole('heading', { name: '2 films demain' })).toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: 'carte ugc' }))
      expect(window.location.search).toBe('?jour=2026-11-24&patrimoine=0&ugc=1')
      expect(screen.getByRole('heading', { name: '1 film demain' })).toBeInTheDocument()
    })

    it('offers to clear the filters when they leave nothing', async () => {
      window.history.replaceState(null, '', '/?ugc=1&salles=etoile')
      render(<App />)
      expect(
        await screen.findByText('rien ce jour-là avec ces filtres. essaie sans « patrimoine » ?'),
      ).toBeInTheDocument()
      const clear = screen.getAllByRole('button', { name: 'tout effacer' })
      fireEvent.click(clear[clear.length - 1])
      expect(window.location.search).toBe('?patrimoine=0')
      expect(screen.getByRole('heading', { name: '2 films aujourd’hui' })).toBeInTheDocument()
    })

    it('drops unknown cinemas from the URL once the cinemas are loaded', async () => {
      window.history.replaceState(null, '', '/?salles=champo,mk2-cultissime')
      render(<App />)
      await screen.findByRole('heading', { name: 'les 2 salles' })
      expect(window.location.search).toBe('?salles=champo')
    })
  })
})
