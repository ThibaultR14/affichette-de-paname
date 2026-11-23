import { describe, expect, it } from 'vitest'
import {
  dayLabel,
  dayTitle,
  formatRuntime,
  parisDate,
  parisDayRange,
  parisTime,
  resolveDay,
  rollingWeek,
  weekStarting,
} from './days'

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

describe('parisDayRange', () => {
  it('maps a Paris day to UTC instants, winter and summer', () => {
    expect(parisDayRange('2026-11-24')).toEqual({
      from: '2026-11-23T23:00:00.000Z',
      to: '2026-11-24T23:00:00.000Z',
    })
    expect(parisDayRange('2026-07-01')).toEqual({
      from: '2026-06-30T22:00:00.000Z',
      to: '2026-07-01T22:00:00.000Z',
    })
  })

  it('handles the 23-hour and 25-hour days', () => {
    // 2026-03-29: clocks go forward; 2026-10-25: clocks go back
    expect(parisDayRange('2026-03-29')).toEqual({
      from: '2026-03-28T23:00:00.000Z',
      to: '2026-03-29T22:00:00.000Z',
    })
    expect(parisDayRange('2026-10-25')).toEqual({
      from: '2026-10-24T22:00:00.000Z',
      to: '2026-10-25T23:00:00.000Z',
    })
  })

  it('crosses a month and a year', () => {
    expect(parisDayRange('2026-12-31').to).toBe('2026-12-31T23:00:00.000Z')
  })
})

describe('dayTitle', () => {
  it('spells the day out', () => {
    expect(dayTitle('2026-11-22', '2026-11-22')).toBe('aujourd’hui')
    expect(dayTitle('2026-11-23', '2026-11-22')).toBe('demain')
    expect(dayTitle('2026-11-25', '2026-11-22')).toBe('mercredi 25')
  })
})

describe('weekStarting', () => {
  it('lists 7 days from the given one, across a month end', () => {
    expect(weekStarting('2026-11-28')).toEqual([
      '2026-11-28',
      '2026-11-29',
      '2026-11-30',
      '2026-12-01',
      '2026-12-02',
      '2026-12-03',
      '2026-12-04',
    ])
  })
})

describe('resolveDay', () => {
  const week = weekStarting('2026-11-23')

  it('keeps a day of the window', () => {
    expect(resolveDay('2026-11-23', week)).toBe('2026-11-23')
    expect(resolveDay('2026-11-29', week)).toBe('2026-11-29')
  })

  it('falls back to today when missing, malformed or outside the window', () => {
    expect(resolveDay(null, week)).toBe('2026-11-23')
    expect(resolveDay('', week)).toBe('2026-11-23')
    expect(resolveDay('demain', week)).toBe('2026-11-23')
    expect(resolveDay('2026-13-40', week)).toBe('2026-11-23')
    expect(resolveDay('2026-11-22', week)).toBe('2026-11-23')
    expect(resolveDay('2026-11-30', week)).toBe('2026-11-23')
  })
})
