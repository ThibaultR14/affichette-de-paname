import { describe, expect, it } from 'vitest'
import { parisDate, rollingWeek } from './days'

describe('parisDate', () => {
  it('uses the Paris calendar day, not UTC', () => {
    // 23:30 UTC on 2026-11-22 is already 00:30 on the 23rd in Paris (UTC+1)
    expect(parisDate(new Date('2026-11-22T23:30:00Z'))).toBe('2026-11-23')
  })
})

describe('rollingWeek', () => {
  it('returns 7 consecutive days starting today', () => {
    expect(rollingWeek(new Date('2026-11-22T10:00:00Z'))).toEqual([
      '2026-11-22',
      '2026-11-23',
      '2026-11-24',
      '2026-11-25',
      '2026-11-26',
      '2026-11-27',
      '2026-11-28',
    ])
  })

  it('crosses month boundaries and the DST change', () => {
    const week = rollingWeek(new Date('2026-10-24T12:00:00Z'))
    expect(week[0]).toBe('2026-10-24')
    expect(week[6]).toBe('2026-10-30')
  })
})
