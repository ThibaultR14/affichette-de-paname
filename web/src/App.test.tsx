import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./lib/cinemas', () => ({
  fetchCinemas: () =>
    Promise.resolve([{ id: 'champo', name: 'Le Champo', arrondissement: 5, acceptsUgc: true }]),
}))

vi.mock('./lib/screenings', () => ({
  fetchDayScreenings: (day: string) => Promise.resolve([day]),
  groupByFilm: () => [
    {
      key: 'raw:nuit des courts',
      tmdbId: null,
      title: 'Nuit des courts',
      cinemas: [],
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
    expect(await screen.findByText('Le Champo')).toBeInTheDocument()
  })
})
