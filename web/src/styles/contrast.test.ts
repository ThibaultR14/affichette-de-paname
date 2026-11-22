// @vitest-environment node
// Contrast of the design tokens in both themes (docs/design.md): WCAG AA, never orange.
// Adapted from Recsys_movie (web/src/styles/contrast.test.ts).
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const css = readFileSync(fileURLToPath(new URL('./tokens.css', import.meta.url)), 'utf8')

function block(selector: string): Record<string, string> {
  const start = css.indexOf(selector)
  if (start < 0) throw new Error(`${selector} missing`)
  const body = css.slice(css.indexOf('{', start) + 1, css.indexOf('}', start))
  return Object.fromEntries(
    [...body.matchAll(/--color-([a-z-]+):\s*(#[0-9a-f]{6})/gi)].map((m) => [m[1], m[2]]),
  )
}

const light = block(':root {')
const darkOnly = block(":root[data-theme='dark']")
const dark = { ...light, ...darkOnly }

function channels(hex: string): number[] {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
}

function luminance(hex: string): number {
  const [r, g, b] = channels(hex)
    .map((x) => x / 255)
    .map((x) => (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(a: string, b: string): number {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

function isOrange(hex: string): boolean {
  const [r, g, b] = channels(hex)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  if (max - min < 60) return false // greys
  if (max !== r) return false
  const hue = (((g - b) / (max - min)) * 60 + 360) % 360
  return hue >= 15 && hue <= 50
}

it('isOrange spots orange and spares the palette', () => {
  expect(isOrange('#e8740c')).toBe(true)
  expect(isOrange('#2546b8')).toBe(false)
  expect(isOrange('#555049')).toBe(false)
})

describe.each([
  ['clair', light],
  ['sombre', dark],
])('thème %s', (_, t) => {
  it('text on the background and on cards: AA (≥ 4.5:1)', () => {
    // badges and chips use ink on surface; pressed chips use paper on ink
    for (const fg of ['ink', 'muted', 'pen']) {
      for (const bg of ['paper', 'surface']) {
        expect(contrast(t[fg], t[bg]), `${fg} sur ${bg}`).toBeGreaterThanOrEqual(4.5)
      }
    }
  })

  it('component borders (ink) ≥ 3:1 on paper and surface', () => {
    expect(contrast(t.ink, t.paper)).toBeGreaterThanOrEqual(3)
    expect(contrast(t.ink, t.surface)).toBeGreaterThanOrEqual(3)
  })

  it('cards one step apart from the background, never orange', () => {
    expect(t.surface).not.toBe(t.paper)
    for (const v of Object.values(t)) expect(isOrange(v), v).toBe(false)
  })
})

it('the dark theme redefines every colour token', () => {
  expect(Object.keys(darkOnly).sort()).toEqual(Object.keys(light).sort())
  expect(Object.keys(light).sort()).toEqual(['ink', 'muted', 'paper', 'pen', 'rule', 'surface'])
})
