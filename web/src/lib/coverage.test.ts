import { describe, expect, it } from 'vitest'
import { coverageDate, coverageStatus, timeAgo } from './coverage'

const NOW = new Date('2026-11-23T14:00:00Z') // 15:00 in Paris
const TODAY = '2026-11-23'

describe('timeAgo', () => {
  const ago = (seconds: number) => timeAgo(new Date(NOW.getTime() - seconds * 1000), NOW)

  it('says « à l’instant » under a minute, or for a date in the future', () => {
    expect(ago(0)).toBe('à l’instant')
    expect(ago(59)).toBe('à l’instant')
    expect(ago(-120)).toBe('à l’instant')
  })

  it('counts minutes, hours, then days, rounded down', () => {
    expect(ago(60)).toBe('il y a 1 min')
    expect(ago(12 * 60 + 59)).toBe('il y a 12 min')
    expect(ago(3 * 3600 + 59 * 60)).toBe('il y a 3 h')
    expect(ago(25 * 3600)).toBe('il y a 1 j')
    expect(ago(3 * 86400)).toBe('il y a 3 j')
  })
})

describe('coverageDate', () => {
  it('writes « ven. 27 » for a date close to today', () => {
    expect(coverageDate('2026-11-27', TODAY)).toBe('ven. 27')
    expect(coverageDate('2026-11-23', TODAY)).toBe('lun. 23')
    expect(coverageDate('2026-11-17', TODAY)).toBe('mar. 17')
  })

  it('adds the month and drops the weekday for an older date', () => {
    expect(coverageDate('2026-11-16', TODAY)).toBe('16 nov.')
    expect(coverageDate('2026-10-02', TODAY)).toBe('2 oct.')
  })
})

describe('coverageStatus', () => {
  const ok = {
    coverageUntil: '2026-11-27',
    lastSuccessAt: '2026-11-23T11:00:00Z',
    lastImportOk: true,
  }

  it('gives the known programme and the last update', () => {
    expect(coverageStatus(ok, TODAY, NOW)).toEqual({
      line: 'programme connu jusqu’au ven. 27 · mis à jour il y a 3 h',
      failed: false,
    })
  })

  it('keeps the last successful import when the latest one failed', () => {
    expect(
      coverageStatus(
        { ...ok, lastSuccessAt: '2026-11-21T14:00:00Z', lastImportOk: false },
        TODAY,
        NOW,
      ),
    ).toEqual({ line: 'programme connu jusqu’au ven. 27 · mis à jour il y a 2 j', failed: true })
  })

  it('has no line for a cinema that always failed', () => {
    expect(
      coverageStatus({ coverageUntil: null, lastSuccessAt: null, lastImportOk: false }, TODAY, NOW),
    ).toEqual({ line: null, failed: true })
  })

  it('says when a cinema was never imported', () => {
    expect(
      coverageStatus({ coverageUntil: null, lastSuccessAt: null, lastImportOk: null }, TODAY, NOW),
    ).toEqual({ line: 'pas encore de programme pour cette salle', failed: false })
  })

  it('gives only the update when no screening was ever imported', () => {
    expect(coverageStatus({ ...ok, coverageUntil: null }, TODAY, NOW)).toEqual({
      line: 'mis à jour il y a 3 h',
      failed: false,
    })
  })
})
