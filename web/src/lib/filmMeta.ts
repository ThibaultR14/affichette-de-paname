import { formatRuntime } from './days'

/** « Jean-Luc Godard, 1963 · 1 h 43 », shared with the film page. */
export function metaLine(directors: string[], year?: number | null, runtimeMin?: number | null) {
  const who = [directors.join(' et '), year].filter(Boolean).join(', ')
  return [who, runtimeMin ? formatRuntime(runtimeMin) : null].filter(Boolean).join(' · ') // the runtime never starts a line
}
