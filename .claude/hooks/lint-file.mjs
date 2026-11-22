// PostToolUse hook (Edit|Write): lint the file Claude just changed.
// Exit 2 + stderr sends the errors back to Claude. Other files are ignored.
import { spawnSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import path from 'node:path'

const input = JSON.parse(readFileSync(0, 'utf8'))
const file = input.tool_input?.file_path
if (!file) process.exit(0)

const root = (process.env.CLAUDE_PROJECT_DIR || process.cwd()).replace(/^[a-z]:/, (d) =>
  d.toUpperCase(),
)
const abs = path.resolve(file).replace(/^[a-z]:/, (d) => d.toUpperCase())
const rel = path.relative(root, abs).split(path.sep).join('/')

// One command line (paths are JSON-quoted below) so Node does not warn about shell + args.
const run = (cwd, cmd, args) =>
  spawnSync([cmd, ...args].join(' '), { cwd: path.join(root, cwd), encoding: 'utf8', shell: true })

const checks = []
if (/^web\/.+\.(ts|tsx|js|mjs|css|json)$/.test(rel) && !rel.includes('node_modules')) {
  const f = JSON.stringify(path.relative(path.join(root, 'web'), abs))
  if (/\.(ts|tsx|js|mjs)$/.test(rel)) checks.push(run('web', 'npx', ['oxlint', f]))
  checks.push(run('web', 'npx', ['prettier', '--check', f]))
} else if (/^pipeline\/.+\.py$/.test(rel)) {
  const f = JSON.stringify(path.relative(path.join(root, 'pipeline'), abs))
  checks.push(run('pipeline', 'uv', ['run', '--quiet', 'ruff', 'check', f]))
  checks.push(run('pipeline', 'uv', ['run', '--quiet', 'ruff', 'format', '--check', f]))
} else {
  process.exit(0)
}

const failed = checks.filter((r) => r.status !== 0)
if (failed.length) {
  process.stderr.write(
    `Lint errors in ${rel}:\n` + failed.map((r) => (r.stdout || '') + (r.stderr || '')).join('\n'),
  )
  process.exit(2)
}
