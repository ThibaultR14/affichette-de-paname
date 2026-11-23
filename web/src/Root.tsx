import { Suspense, lazy } from 'react'
import App from './App'
import { AccountBar } from './components/AccountBar'
import { parseRoute, usePathname, type Route } from './lib/router'
import { NotFound } from './pages/NotFound'

// Pages other than home are loaded lazily.
const Styleguide = lazy(() => import('./pages/Styleguide'))
const FilmPage = lazy(() => import('./pages/FilmPage').then((m) => ({ default: m.FilmPage })))
const LoginPage = lazy(() => import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })))

function Page({ route }: { route: Route }) {
  switch (route.page) {
    case 'home':
      return <App />
    case 'styleguide':
      return (
        <Suspense fallback={null}>
          <Styleguide />
        </Suspense>
      )
    case 'login':
      return (
        <Suspense fallback={null}>
          <LoginPage />
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

export default function Root() {
  const route = parseRoute(usePathname())
  return (
    <>
      {/* The login page shows the account state itself. */}
      {route.page !== 'login' && <AccountBar />}
      <Page route={route} />
    </>
  )
}
