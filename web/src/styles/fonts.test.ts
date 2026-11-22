// @vitest-environment node
// Fonts are self-hosted (@fontsource): no request to Google Fonts (docs/design.md).
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, it } from 'vitest'

const web = fileURLToPath(new URL('../..', import.meta.url))
const google = /fonts\.(googleapis|gstatic)\.com/

function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const path = join(dir, e.name)
    if (e.isDirectory()) return sources(path)
    return /\.(css|tsx?|html)$/.test(e.name) && !e.name.endsWith('.test.ts') ? [path] : []
  })
}

it('no Google Fonts URL in index.html or src/', () => {
  for (const file of [join(web, 'index.html'), ...sources(join(web, 'src'))]) {
    expect(readFileSync(file, 'utf8'), file).not.toMatch(google)
  }
})

it('tokens.css imports Courier Prime and Caveat from @fontsource', () => {
  const css = readFileSync(join(web, 'src/styles/tokens.css'), 'utf8')
  expect(css).toContain("@import '@fontsource/courier-prime/400.css'")
  expect(css).toContain("@import '@fontsource/courier-prime/700.css'")
  expect(css).toContain("@import '@fontsource/caveat/500.css'")
})
