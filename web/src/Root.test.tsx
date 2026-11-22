import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Root from './Root'

describe('Root', () => {
  it('serves the styleguide on /styleguide, with or without a trailing slash', async () => {
    render(<Root pathname="/styleguide/" />)
    expect(await screen.findByRole('heading', { level: 1, name: 'styleguide' })).toBeInTheDocument()
  })

  it('serves the home page elsewhere', () => {
    render(<Root pathname="/" />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent("l'affichette de paname")
  })
})
