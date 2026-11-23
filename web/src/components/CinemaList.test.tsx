import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CinemaWithCoverage } from '../lib/cinemas'
import { CinemaList } from './CinemaList'

const NOW = new Date('2026-11-23T14:00:00Z') // lundi, 15:00 in Paris
const fresh = {
  coverageUntil: '2026-11-27',
  lastSuccessAt: '2026-11-23T11:00:00Z',
  lastImportOk: true,
}
const cinemas: CinemaWithCoverage[] = Array.from({ length: 19 }, (_, i) => ({
  id: `salle-${i}`,
  name: `Salle ${i}`,
  arrondissement: 5,
  acceptsUgc: true,
  ...fresh,
}))
cinemas[18] = {
  id: 'etoile',
  name: "Club de l'Étoile",
  arrondissement: 17,
  acceptsUgc: false,
  ...fresh,
}
const FAILED = '(on n’a pas pu mettre à jour cette salle aujourd’hui)'

describe('CinemaList', () => {
  it('says it is loading first', () => {
    render(<CinemaList load={() => new Promise(() => {})} />)
    expect(screen.getByText('on déplie l’affichette…')).toBeInTheDocument()
  })

  it('lists every cinema with its arrondissement and the ugc badge', async () => {
    render(<CinemaList load={() => Promise.resolve(cinemas)} />)
    expect(await screen.findByRole('heading', { name: 'les 19 salles' })).toBeInTheDocument()
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(19)
    expect(within(items[0]).getByText('ugc')).toBeInTheDocument()
    expect(within(items[0]).getByText('5e')).toBeInTheDocument()
    const etoile = items[18]
    expect(etoile).toHaveTextContent("Club de l'Étoile")
    expect(within(etoile).getByText('17e')).toBeInTheDocument()
    expect(within(etoile).queryByText('ugc')).not.toBeInTheDocument()
  })

  it('writes 1er for the first arrondissement', async () => {
    render(<CinemaList load={() => Promise.resolve([{ ...cinemas[0], arrondissement: 1 }])} />)
    expect(await screen.findByText('1er')).toBeInTheDocument()
  })

  it('shows how far the programme of each cinema is known', async () => {
    render(<CinemaList load={() => Promise.resolve(cinemas)} now={NOW} />)
    const items = await screen.findAllByRole('listitem')
    expect(
      within(items[0]).getByText('programme connu jusqu’au ven. 27 · mis à jour il y a 3 h'),
    ).toBeInTheDocument()
    expect(within(items[0]).queryByText(FAILED)).not.toBeInTheDocument()
  })

  it('says when the latest import of a cinema failed, with the last known programme', async () => {
    const failed = { ...cinemas[0], lastSuccessAt: '2026-11-21T14:00:00Z', lastImportOk: false }
    render(<CinemaList load={() => Promise.resolve([failed])} now={NOW} />)
    expect(await screen.findByText(FAILED)).toBeInTheDocument()
    expect(
      screen.getByText('programme connu jusqu’au ven. 27 · mis à jour il y a 2 j'),
    ).toBeInTheDocument()
  })

  it('says when a cinema has never been imported', async () => {
    const never = { ...cinemas[0], coverageUntil: null, lastSuccessAt: null, lastImportOk: null }
    render(<CinemaList load={() => Promise.resolve([never])} now={NOW} />)
    expect(await screen.findByText('pas encore de programme pour cette salle')).toBeInTheDocument()
  })

  it('says so when there is no cinema yet', async () => {
    render(<CinemaList load={() => Promise.resolve([])} />)
    expect(
      await screen.findByText('(pas encore de salle ici, reviens bientôt)'),
    ).toBeInTheDocument()
  })

  it('loads only once across re-renders', async () => {
    const load = vi.fn(() => Promise.resolve(cinemas))
    const { rerender } = render(<CinemaList load={load} />)
    await screen.findByRole('heading', { name: 'les 19 salles' })
    rerender(<CinemaList load={() => Promise.resolve(cinemas)} />)
    expect(load).toHaveBeenCalledTimes(1)
  })

  it('apologises when the database cannot be reached', async () => {
    render(<CinemaList load={() => Promise.reject(new Error('offline'))} />)
    expect(
      await screen.findByText('(on n’arrive pas à joindre la base, réessaie plus tard)'),
    ).toBeInTheDocument()
  })
})
