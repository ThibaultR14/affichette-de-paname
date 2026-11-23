import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DEFAULT_FILTERS, NO_FILTERS, type Filters } from '../lib/filters'
import type { Cinema } from '../lib/cinemas'
import { FilterPanel } from './FilterPanel'

const cinemas: Cinema[] = [
  { id: 'louxor', name: 'Le Louxor', arrondissement: 10, acceptsUgc: true },
  { id: 'champo', name: 'Le Champo', arrondissement: 5, acceptsUgc: true },
  { id: 'etoile', name: "Club de l'Étoile", arrondissement: 17, acceptsUgc: false },
]

function setup(filters: Filters = DEFAULT_FILTERS) {
  const onChange = vi.fn()
  render(<FilterPanel cinemas={cinemas} filters={filters} onChange={onChange} />)
  return onChange
}

function openPanel() {
  fireEvent.click(screen.getByRole('button', { name: 'affiner' }))
}

describe('FilterPanel', () => {
  it('is folded by default and unfolds under the button', () => {
    setup()
    const toggle = screen.getByRole('button', { name: 'affiner' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('button', { name: 'carte ugc' })).not.toBeInTheDocument()
    openPanel()
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(document.getElementById(toggle.getAttribute('aria-controls')!)).toBeInTheDocument()
  })

  it('shows heritage pressed by default and the cinemas by name', () => {
    setup()
    openPanel()
    expect(screen.getByRole('button', { name: 'patrimoine (+ de 20 ans)' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: 'carte ugc' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    const names = screen.getAllByRole('button', { name: /^(le |club)/ }).map((b) => b.textContent)
    expect(names).toEqual(["club de l'étoile", 'le champo', 'le louxor'])
  })

  it('toggles heritage, ugc and a cinema', () => {
    const onChange = setup({ cinemas: ['champo'], ugc: false, heritage: true })
    openPanel()
    fireEvent.click(screen.getByRole('button', { name: 'patrimoine (+ de 20 ans)' }))
    expect(onChange).toHaveBeenLastCalledWith({ cinemas: ['champo'], ugc: false, heritage: false })
    fireEvent.click(screen.getByRole('button', { name: 'carte ugc' }))
    expect(onChange).toHaveBeenLastCalledWith({ cinemas: ['champo'], ugc: true, heritage: true })
    fireEvent.click(screen.getByRole('button', { name: 'le louxor' }))
    expect(onChange).toHaveBeenLastCalledWith({
      cinemas: ['champo', 'louxor'],
      ugc: false,
      heritage: true,
    })
    fireEvent.click(screen.getByRole('button', { name: 'le champo' }))
    expect(onChange).toHaveBeenLastCalledWith({ cinemas: [], ugc: false, heritage: true })
  })

  it('lists active filters as removable chips, with « tout effacer »', () => {
    const onChange = setup({ cinemas: ['louxor'], ugc: true, heritage: true })
    fireEvent.click(screen.getByRole('button', { name: 'retirer le filtre le louxor' }))
    expect(onChange).toHaveBeenLastCalledWith({ cinemas: [], ugc: true, heritage: true })
    fireEvent.click(screen.getByRole('button', { name: 'retirer le filtre carte ugc' }))
    expect(onChange).toHaveBeenLastCalledWith({ cinemas: ['louxor'], ugc: false, heritage: true })
    fireEvent.click(screen.getByRole('button', { name: 'retirer le filtre patrimoine' }))
    expect(onChange).toHaveBeenLastCalledWith({ cinemas: ['louxor'], ugc: true, heritage: false })
    fireEvent.click(screen.getByRole('button', { name: 'tout effacer' }))
    expect(onChange).toHaveBeenLastCalledWith(NO_FILTERS)
  })

  it('shows no active chip and no « tout effacer » without filters', () => {
    setup(NO_FILTERS)
    expect(screen.queryByRole('button', { name: /^retirer le filtre/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'tout effacer' })).not.toBeInTheDocument()
  })

  it('names a cinema by its id until the list is loaded', () => {
    const onChange = vi.fn()
    render(
      <FilterPanel
        cinemas={[]}
        filters={{ ...NO_FILTERS, cinemas: ['brady'] }}
        onChange={onChange}
      />,
    )
    expect(screen.getByRole('button', { name: 'retirer le filtre brady' })).toBeInTheDocument()
  })
})
