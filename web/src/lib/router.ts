import {
  createElement,
  useEffect,
  useState,
  type AnchorHTMLAttributes,
  type MouseEvent,
} from 'react'

/**
 * Tiny client-side router: a handful of routes do not need a dependency.
 * `navigate` pushes a history entry (the film page must be reachable with « back »),
 * `usePathname` re-renders on navigation and on popstate.
 */
export type Route =
  | { page: 'home' }
  | { page: 'styleguide' }
  | { page: 'login' }
  | { page: 'film'; tmdbId: number }
  | { page: 'not-found' }

/** TMDB ids are positive integers; 10 digits at most keeps them in Postgres `integer`. */
const FILM = /^\/film\/([1-9]\d{0,9})$/
const MAX_INT = 2_147_483_647

export function parseRoute(pathname: string): Route {
  const path = pathname.replace(/\/+$/, '')
  if (path === '') return { page: 'home' }
  if (path === '/styleguide') return { page: 'styleguide' }
  if (path === '/connexion') return { page: 'login' }
  const film = FILM.exec(path)
  if (film && Number(film[1]) <= MAX_INT) return { page: 'film', tmdbId: Number(film[1]) }
  return { page: 'not-found' }
}

const NAVIGATE = 'affichette:navigate'

/** Marks entries pushed by the site, so « back » can tell whether it stays on the site. */
const FROM_SITE = { fromSite: true }

export function navigate(path: string) {
  window.history.pushState(FROM_SITE, '', path)
  window.dispatchEvent(new Event(NAVIGATE))
}

/** True when the current entry was reached from another page of the site. */
export function cameFromSite(): boolean {
  return (window.history.state as { fromSite?: boolean } | null)?.fromSite === true
}

export function usePathname(): string {
  const [pathname, setPathname] = useState(() => window.location.pathname)
  useEffect(() => {
    const sync = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', sync)
    window.addEventListener(NAVIGATE, sync)
    return () => {
      window.removeEventListener('popstate', sync)
      window.removeEventListener(NAVIGATE, sync)
    }
  }, [])
  return pathname
}

/** A real `<a href>` (new tab, copy link) that navigates in place on a plain click. */
export function Link({
  href,
  onClick,
  ...rest
}: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const handle = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e)
    if (
      e.defaultPrevented ||
      e.button !== 0 ||
      e.metaKey ||
      e.ctrlKey ||
      e.shiftKey ||
      e.altKey ||
      (rest.target && rest.target !== '_self')
    )
      return
    e.preventDefault()
    navigate(href)
    window.scrollTo(0, 0)
  }
  return createElement('a', { ...rest, href, onClick: handle })
}
