import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import Styleguide from './Styleguide'

it('shows every base component', () => {
  render(<Styleguide />)
  expect(screen.getByRole('heading', { level: 1, name: 'styleguide' })).toBeInTheDocument()
  for (const section of [
    'couleurs',
    'typo',
    'boutons',
    'puces',
    'pastilles',
    'bandeau des 7 jours',
    "couverture d'une salle",
    'cartes film',
  ]) {
    expect(screen.getByRole('heading', { level: 2, name: section })).toBeInTheDocument()
  }
  expect(screen.getByRole('navigation', { name: 'jours' })).toBeInTheDocument()
  expect(screen.getAllByRole('article')).toHaveLength(3)
  expect(screen.getByRole('button', { name: /passer en/ })).toBeInTheDocument()
})
