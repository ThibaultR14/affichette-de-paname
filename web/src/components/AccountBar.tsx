import { LOGIN_PATH, signOut, useSession, type AuthApi } from '../lib/auth'
import { Link } from '../lib/router'
import { supabase } from '../lib/supabase'
import './AccountBar.css'

/** Top-right of every page: « connexion », or the signed-in email and « se déconnecter ». */
export function AccountBar({ auth = supabase?.auth ?? null }: { auth?: AuthApi | null }) {
  const session = useSession(auth)
  // Nothing while the session is read (no flash of « connexion » for a signed-in user),
  // nor when the site has no Supabase client at all.
  if (session === undefined || !auth) return null
  return (
    <nav className="account-bar" aria-label="compte">
      {session ? (
        <>
          <span className="account-bar__email">{session.user.email}</span>
          <button type="button" className="link-button" onClick={() => void signOut(auth)}>
            se déconnecter
          </button>
        </>
      ) : (
        <Link href={LOGIN_PATH} className="account-bar__link">
          connexion
        </Link>
      )}
    </nav>
  )
}
