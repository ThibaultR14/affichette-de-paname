import { act } from '@testing-library/react'
import type { AuthChangeEvent, Session } from '@supabase/supabase-js'
import { vi } from 'vitest'
import type { AuthApi } from '../lib/auth'

type Listener = (event: AuthChangeEvent, session: Session | null) => void

/** A fake supabase-js auth: `emit` plays the role of the client firing auth events. */
export function fakeAuth(otpError: { status?: number; code?: string } | null = null) {
  let listener: Listener | null = null
  const unsubscribe = vi.fn()
  const auth = {
    onAuthStateChange: vi.fn((cb: Listener) => {
      listener = cb
      return { data: { subscription: { unsubscribe } } }
    }),
    signInWithOtp: vi.fn(() => Promise.resolve({ data: {}, error: otpError })),
    signOut: vi.fn(() => {
      listener?.('SIGNED_OUT', null)
      return Promise.resolve({ error: null })
    }),
  }
  return {
    auth: auth as unknown as AuthApi,
    mocks: auth,
    unsubscribe,
    emit: (event: AuthChangeEvent, session: Session | null) =>
      act(() => listener?.(event, session)),
  }
}

export const session = { user: { email: 'cinephile@example.com' } } as Session
