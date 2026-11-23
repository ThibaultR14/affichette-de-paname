import { Suspense, lazy } from 'react'
import App from './App'
import { parseRoute, usePathname } from './lib/router'
import { NotFound } from './pages/NotFound'

// Pages other than home are loaded lazily.
const Styleguide = lazy(() => import('./pages/Styleguide'))
const FilmPage = lazy(() => import('./pages/FilmPage').then((m) => ({ default: m.FilmPage })))

export default function Root() {
  const route = parseRoute(usePathname())
  switch (route.page) {
    case 'home':
      return <App />
    case 'styleguide':
      return (
        <Suspense fallback={null}>
          <Styleguide />
        </Suspense>
      )
    case 'film':
      return (
        <Suspense fallback={null}>
          {/* keyed: another film starts from a fresh page */}
          <FilmPage key={route.tmdbId} tmdbId={route.tmdbId} />
        </Suspense>
      )
    case 'not-found':
      return <NotFound />
  }
}
