import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { fakeAuth, session } from '../test-utils/fakeAuth'
import { LoginPage } from './LoginPage'

afterEach(() => window.history.replaceState(null, '', '/'))

function signedOut(otpError: { status?: number; code?: string } | null = null) {
  const fake = fakeAuth(otpError)
  render(<LoginPage auth={fake.auth} />)
  fake.emit('INITIAL_SESSION', null)
  return fake
}

function submit(email: string) {
  fireEvent.change(screen.getByLabelText('ton email'), { target: { value: email } })
  fireEvent.click(screen.getByRole('button', { name: 'envoie-moi le lien' }))
}

describe('LoginPage', () => {
  it('waits for the stored session before showing anything', () => {
    render(<LoginPage auth={fakeAuth().auth} />)
    expect(screen.getByText('on vérifie si on te connaît…')).toBeInTheDocument()
    expect(screen.queryByLabelText('ton email')).not.toBeInTheDocument()
  })

  it('sends the link, then says to check the mails', async () => {
    const { mocks } = signedOut()
    expect(
      screen.getByText('on t’envoie un lien par mail, pas de mot de passe.'),
    ).toBeInTheDocument()
    submit('cinephile@example.com')
    expect(await screen.findByText(/c’est parti\. regarde tes mails/)).toHaveTextContent(
      'cinephile@example.com',
    )
    expect(mocks.signInWithOtp).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('button', { name: 'pas reçu ? recommencer' }))
    expect(screen.getByLabelText('ton email')).toHaveValue('cinephile@example.com')
  })

  it('says to slow down when Supabase rate-limits the mails', async () => {
    signedOut({ status: 429, code: 'over_email_send_rate_limit' })
    submit('cinephile@example.com')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'doucement, réessaie dans une minute',
    )
    expect(screen.getByLabelText('ton email')).toHaveAttribute('aria-describedby', 'login-error')
  })

  it('shows the error of an expired link and cleans the URL', () => {
    window.history.replaceState(
      null,
      '',
      '/connexion#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid',
    )
    signedOut()
    expect(screen.getByRole('alert')).toHaveTextContent('ce lien a expiré ou a déjà servi')
    expect(window.location.hash).toBe('')
    expect(window.location.pathname).toBe('/connexion')
  })

  it('shows the signed-in email and signs out', () => {
    const { auth, emit, mocks } = fakeAuth()
    render(<LoginPage auth={auth} />)
    emit('INITIAL_SESSION', session)
    expect(screen.getByText(/c’est bon, on t’a reconnu/)).toHaveTextContent('cinephile@example.com')
    expect(screen.getByRole('link', { name: 'voir les séances' })).toHaveAttribute('href', '/')

    fireEvent.click(screen.getByRole('button', { name: 'se déconnecter' }))
    expect(mocks.signOut).toHaveBeenCalledWith({ scope: 'local' })
    expect(screen.getByLabelText('ton email')).toBeInTheDocument()
  })

  it('goes back to the form after signing out, even if a link was sent from this tab', async () => {
    const { emit } = signedOut()
    submit('cinephile@example.com')
    await screen.findByText(/c’est parti/)
    emit('SIGNED_IN', session) // the link was opened in another tab of the same browser
    fireEvent.click(screen.getByRole('button', { name: 'se déconnecter' }))
    expect(screen.getByLabelText('ton email')).toBeInTheDocument()
  })

  it('sets the page title', () => {
    signedOut()
    expect(document.title).toBe('connexion · l’affichette de paname')
  })
})
