// Windows: when started from "c:\..." (lowercase drive, as VS Code does), Vitest loads two
// copies of its runner and every suite fails with "Cannot read properties of undefined
// (reading 'config')". Relaunch Vitest from the same path with an uppercase drive letter.
import { spawnSync } from 'node:child_process'

const cwd = process.cwd().replace(/^[a-z]:/, (d) => d.toUpperCase())
const args = process.argv.slice(2).map((a) => JSON.stringify(a))
const { status } = spawnSync(['npx', 'vitest', ...args].join(' '), {
  cwd,
  stdio: 'inherit',
  shell: true,
})
process.exit(status ?? 1)
