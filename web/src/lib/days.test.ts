import { describe, expect, it } from 'vitest'
import { dayLabel, formatRuntime, parisDate, parisTime, rollingWeek } from './days'

describe('parisTime', () => {
  it('formats in Paris time, winter and summer', () => {
    expect(parisTime(new Date('2026-11-22T13:00:00Z'))).toBe('14:00')
    expect(parisTime(new Date('2026-07-01T18:30:00Z'))).toBe('20:30')
    expect(parisTime(new Date('2026-11-22T23:05:00Z'))).toBe('00:05')
  })
})

describe('formatRuntime', () => {
  const spaced = (s: string) => s.replaceAll(' ', ' ')

  it('writes hours and minutes', () => {
    expect(spaced(formatRuntime(105))).toBe('1 h 45')
    expect(spaced(formatRuntime(125))).toBe('2 h 05')
    expect(spaced(formatRuntime(120))).toBe('2 h')
    expect(spaced(formatRuntime(52))).toBe('52 min')
  })

  it('never breaks inside a runtime', () => {
    expect(formatRuntime(105)).not.toContain(' ')
  })
})

describe('dayLabel', () => {
  it('names today and tomorrow, then weekday and day number', () => {
    expect(dayLabel('2026-11-22', '2026-11-22')).toBe('auj.')
    expect(dayLabel('2026-11-23', '2026-11-22')).toBe('dem.')
    expect(dayLabel('2026-11-25', '2026-11-22')).toBe('mer. 25')
    expect(dayLabel('2026-11-28', '2026-11-22')).toBe('sam. 28')
  })

  it('works across a month boundary', () => {
    expect(dayLabel('2026-12-01', '2026-11-30')).toBe('dem.')
    expect(dayLabel('2026-12-02', '2026-11-30')).toBe('mer. 2')
  })
})

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
