import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./lib/cinemas', () => ({
  fetchCinemas: () =>
    Promise.resolve([{ id: 'champo', name: 'Le Champo', arrondissement: 5, acceptsUgc: true }]),
}))

describe('App', () => {
  it('shows the site name', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent("l'affichette de paname")
  })

  it('lists the cinemas read from Supabase', async () => {
    render(<App />)
    expect(await screen.findByText('Le Champo')).toBeInTheDocument()
  })
})
