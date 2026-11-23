import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { fakeAuth, session } from '../test-utils/fakeAuth'
import { readLinkError, sendMagicLink, signOut, useSession } from './auth'

describe('useSession', () => {
  it('is undefined until supabase-js reports the stored session, then follows auth events', () => {
    const { auth, emit, unsubscribe } = fakeAuth()
    const { result, unmount } = renderHook(() => useSession(auth))
    expect(result.current).toBeUndefined()
    emit('INITIAL_SESSION', session)
    expect(result.current).toBe(session)
    emit('SIGNED_OUT', null)
    expect(result.current).toBeNull()
    unmount()
    expect(unsubscribe).toHaveBeenCalled()
  })

  it('is null without a Supabase client', () => {
    const { result } = renderHook(() => useSession(null))
    expect(result.current).toBeNull()
  })
})

describe('sendMagicLink', () => {
  it('asks for a link that comes back to /connexion and creates the account if needed', async () => {
    const { auth, mocks } = fakeAuth()
    await expect(sendMagicLink('  cinephile@example.com ', auth)).resolves.toBe('sent')
    expect(mocks.signInWithOtp).toHaveBeenCalledWith({
      email: 'cinephile@example.com',
      options: { emailRedirectTo: `${window.location.origin}/connexion`, shouldCreateUser: true },
    })
  })

  it.each([
    [{ status: 429, code: 'over_email_send_rate_limit' }, 'rate-limited'],
    [{ status: 400, code: 'email_address_invalid' }, 'invalid-email'],
    [{ status: 500, code: 'unexpected_failure' }, 'error'],
  ])('maps %o to %s', async (otpError, expected) => {
    const { auth } = fakeAuth(otpError)
    await expect(sendMagicLink('a@b.fr', auth)).resolves.toBe(expected)
  })

  it('reports an error when the network is down or there is no client', async () => {
    const { auth, mocks } = fakeAuth()
    mocks.signInWithOtp.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await expect(sendMagicLink('a@b.fr', auth)).resolves.toBe('error')
    await expect(sendMagicLink('a@b.fr', null)).resolves.toBe('error')
  })
})

describe('signOut', () => {
  it('signs out this browser only', async () => {
    const { auth, mocks } = fakeAuth()
    await signOut(auth)
    expect(mocks.signOut).toHaveBeenCalledWith({ scope: 'local' })
  })
})

describe('readLinkError', () => {
  it.each([
    [
      '#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid',
      '',
      'expired',
    ],
    ['#error=server_error&error_description=oops', '', 'failed'],
    ['', '?error=access_denied&error_code=otp_expired', 'expired'],
    ['#access_token=abc&type=magiclink', '', null],
    ['', '', null],
  ])('%s %s → %s', (hash, search, expected) => {
    expect(readLinkError(hash, search)).toBe(expected)
  })
})
