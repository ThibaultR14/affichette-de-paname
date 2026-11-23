/** Replaces the query string without a history entry (filters and days must not fill « back »). */
export function replaceSearch(search: string) {
  const { pathname, hash } = window.location
  window.history.replaceState(window.history.state, '', `${pathname}${search}${hash}`)
}
