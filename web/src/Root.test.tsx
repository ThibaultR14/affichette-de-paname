import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Root from './Root'
import { navigate } from './lib/router'

vi.mock('./lib/films', () => ({
  fetchFilm: vi.fn(() => Promise.resolve(null)),
  fetchFilmScreenings: vi.fn(() => Promise.resolve([])),
  groupByDay: () => [],
}))

// No real Supabase client in tests (the env of .env.local would make one).
vi.mock('./lib/supabase', () => ({ supabase: null }))

function at(path: string) {
  window.history.replaceState(null, '', path)
}

afterEach(() => at('/'))

describe('Root', () => {
  it('serves the styleguide on /styleguide, with or without a trailing slash', async () => {
    at('/styleguide/')
    render(<Root />)
    expect(await screen.findByRole('heading', { level: 1, name: 'styleguide' })).toBeInTheDocument()
  })

  it('serves the login page on /connexion', async () => {
    at('/connexion')
    render(<Root />)
    expect(await screen.findByRole('heading', { level: 1, name: 'connexion' })).toBeInTheDocument()
  })

  it('serves the home page on /', () => {
    render(<Root />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent("l'affichette de paname")
  })

  it('serves the film page on /film/:tmdbId (404 for a film the site does not know)', async () => {
    at('/film/999')
    render(<Root />)
    expect(
      await screen.findByRole('heading', { level: 1, name: 'film introuvable' }),
    ).toBeInTheDocument()
  })

  it.each(['/film/abc', '/nimporte'])('serves a clean 404 on %s', (path) => {
    at(path)
    render(<Root />)
    expect(screen.getByRole('heading', { level: 1, name: 'page introuvable' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'retour à l’accueil' })).toHaveAttribute('href', '/')
  })

  it('follows in-site navigation without reloading', async () => {
    at('/nimporte')
    render(<Root />)
    act(() => navigate('/film/999'))
    expect(await screen.findByRole('heading', { name: 'film introuvable' })).toBeInTheDocument()
  })
})
