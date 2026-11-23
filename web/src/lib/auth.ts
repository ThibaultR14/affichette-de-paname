import type { Session, SupabaseClient } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { supabase } from './supabase'

/** The part of supabase-js auth the site uses (a fake one in tests). */
export type AuthApi = Pick<
  SupabaseClient['auth'],
  'onAuthStateChange' | 'signInWithOtp' | 'signOut'
>

const defaultAuth: AuthApi | null = supabase?.auth ?? null

/** Where the magic link brings the user back: the login page shows the result. */
export const LOGIN_PATH = '/connexion'

/**
 * Current session: `undefined` while supabase-js reads it from storage, `null` when signed out.
 * supabase-js keeps the session in localStorage and refreshes it, so it survives a reload.
 */
export function useSession(auth: AuthApi | null = defaultAuth): Session | null | undefined {
  const [session, setSession] = useState<Session | null | undefined>(auth ? undefined : null)
  useEffect(() => {
    if (!auth) return
    // Fires INITIAL_SESSION right away, then every sign-in, refresh and sign-out (other tabs too).
    const {
      data: { subscription },
    } = auth.onAuthStateChange((_event, s) => setSession(s))
    return () => subscription.unsubscribe()
  }, [auth])
  return session
}

export type SendResult = 'sent' | 'invalid-email' | 'rate-limited' | 'error'

/** Sends the magic link (creates the account on the first sign-in; the trigger adds the profile). */
export async function sendMagicLink(
  email: string,
  auth: AuthApi | null = defaultAuth,
): Promise<SendResult> {
  if (!auth) return 'error'
  try {
    const { error } = await auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: `${window.location.origin}${LOGIN_PATH}`,
        shouldCreateUser: true,
      },
    })
    if (!error) return 'sent'
    if (error.status === 429 || error.code === 'over_email_send_rate_limit') return 'rate-limited'
    if (error.code === 'email_address_invalid' || error.code === 'validation_failed')
      return 'invalid-email'
    return 'error'
  } catch {
    return 'error' // network down
  }
}

/** Signs out this browser only (other devices keep their session). */
export async function signOut(auth: AuthApi | null = defaultAuth): Promise<void> {
  await auth?.signOut({ scope: 'local' })
}

export type LinkError = 'expired' | 'failed'

/**
 * Error carried back by a magic link that did not work (`#error_code=otp_expired…`, or in the
 * query string), or null. supabase-js does not clear it, the login page does.
 */
export function readLinkError(hash: string, search = ''): LinkError | null {
  for (const part of [hash.replace(/^#/, ''), search.replace(/^\?/, '')]) {
    const params = new URLSearchParams(part)
    if (!params.has('error') && !params.has('error_code')) continue
    return params.get('error_code') === 'otp_expired' ? 'expired' : 'failed'
  }
  return null
}
