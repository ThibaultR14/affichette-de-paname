import { Suspense, lazy } from 'react'
import App from './App'

// No router yet (it comes with the main view): /styleguide is the only other page, loaded lazily.
const Styleguide = lazy(() => import('./pages/Styleguide'))

export default function Root({ pathname }: { pathname: string }) {
  if (pathname.replace(/\/+$/, '') === '/styleguide') {
    return (
      <Suspense fallback={null}>
        <Styleguide />
      </Suspense>
    )
  }
  return <App />
}
