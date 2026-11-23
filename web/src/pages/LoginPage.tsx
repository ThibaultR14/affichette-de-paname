import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '../components/Button'
import {
  readLinkError,
  sendMagicLink,
  signOut,
  useSession,
  type AuthApi,
  type SendResult,
} from '../lib/auth'
import { supabase } from '../lib/supabase'
import { Link } from '../lib/router'
import './LoginPage.css'

const ERRORS: Record<Exclude<SendResult, 'sent'> | 'expired' | 'failed', string> = {
  'invalid-email': '(cette adresse a l’air bizarre, vérifie-la)',
  'rate-limited': '(doucement, réessaie dans une minute)',
  error: '(on n’arrive pas à envoyer le lien, réessaie plus tard)',
  expired: '(ce lien a expiré ou a déjà servi, demandes-en un nouveau)',
  failed: '(la connexion n’a pas marché, redemande un lien)',
}

type Phase = 'form' | 'sending' | 'sent'

/** /connexion: magic link form, « check your mail », and the signed-in state. */
export function LoginPage({ auth = supabase?.auth ?? null }: { auth?: AuthApi | null }) {
  const session = useSession(auth)
  const [email, setEmail] = useState('')
  const [phase, setPhase] = useState<Phase>('form')
  // A link that did not work comes back with its error in the URL: shown from the first render.
  const [error, setError] = useState<string | null>(() => {
    const linkError = readLinkError(window.location.hash, window.location.search)
    return linkError ? ERRORS[linkError] : null
  })

  useEffect(() => {
    const previous = document.title
    document.title = 'connexion · l’affichette de paname'
    return () => {
      document.title = previous
    }
  }, [])

  // ...then cleaned from the URL (a reload must not show it again).
  useEffect(() => {
    if (readLinkError(window.location.hash, window.location.search))
      window.history.replaceState(window.history.state, '', window.location.pathname)
  }, [])

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setPhase('sending')
    setError(null)
    const result = await sendMagicLink(email, auth)
    if (result === 'sent') {
      setPhase('sent')
    } else {
      setPhase('form')
      setError(ERRORS[result])
    }
  }

  if (session === undefined) {
    return (
      <main className="login">
        <h1>connexion</h1>
        <p className="login__muted">on vérifie si on te connaît…</p>
      </main>
    )
  }

  if (session) {
    return (
      <main className="login">
        <h1>connexion</h1>
        <p>
          c’est bon, on t’a reconnu : <strong className="login__email">{session.user.email}</strong>
          .
        </p>
        <p className="login__actions">
          <Link href="/">voir les séances</Link>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              // A link opened in another tab signs this one in too: back to the form, not « sent ».
              setPhase('form')
              void signOut(auth)
            }}
          >
            se déconnecter
          </button>
        </p>
      </main>
    )
  }

  if (phase === 'sent') {
    return (
      <main className="login">
        <h1>connexion</h1>
        <p>
          c’est parti. regarde tes mails (et les spams) : le lien pour{' '}
          <strong>{email.trim()}</strong> marche une heure.
        </p>
        <p>
          <button type="button" className="link-button" onClick={() => setPhase('form')}>
            pas reçu ? recommencer
          </button>
        </p>
      </main>
    )
  }

  return (
    <main className="login">
      <h1>connexion</h1>
      <p>on t’envoie un lien par mail, pas de mot de passe.</p>
      <form className="login__form" onSubmit={submit}>
        <label htmlFor="login-email">ton email</label>
        <input
          id="login-email"
          className="login__input"
          type="email"
          name="email"
          autoComplete="email"
          inputMode="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          aria-describedby={error ? 'login-error' : undefined}
        />
        <Button type="submit" disabled={phase === 'sending'}>
          {phase === 'sending' ? 'on envoie…' : 'envoie-moi le lien'}
        </Button>
      </form>
      {error && (
        <p id="login-error" className="hand login__error" role="alert">
          {error}
        </p>
      )}
    </main>
  )
}
