import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { fakeAuth, session } from '../test-utils/fakeAuth'
import { AccountBar } from './AccountBar'

describe('AccountBar', () => {
  it('shows nothing while the session is read, nor without a Supabase client', () => {
    const { container } = render(<AccountBar auth={fakeAuth().auth} />)
    expect(container).toBeEmptyDOMElement()
    const { container: none } = render(<AccountBar auth={null} />)
    expect(none).toBeEmptyDOMElement()
  })

  it('links to /connexion when signed out', () => {
    const { auth, emit } = fakeAuth()
    render(<AccountBar auth={auth} />)
    emit('INITIAL_SESSION', null)
    expect(screen.getByRole('link', { name: 'connexion' })).toHaveAttribute('href', '/connexion')
  })

  it('shows the email and signs out when signed in', () => {
    const { auth, emit, mocks } = fakeAuth()
    render(<AccountBar auth={auth} />)
    emit('INITIAL_SESSION', session)
    expect(screen.getByText('cinephile@example.com')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'se déconnecter' }))
    expect(mocks.signOut).toHaveBeenCalledWith({ scope: 'local' })
    expect(screen.getByRole('link', { name: 'connexion' })).toBeInTheDocument()
  })
})
