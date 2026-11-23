import { useEffect, useState } from 'react'
import { fetchCinemas, type CinemaWithCoverage } from '../lib/cinemas'
import { parisDate } from '../lib/days'
import { Badge } from './Badge'
import { CoverageLine } from './CoverageLine'
import './CinemaList.css'

type State =
  { status: 'loading' } | { status: 'error' } | { status: 'ok'; cinemas: CinemaWithCoverage[] }

function arrondissementLabel(n: number) {
  return n === 1 ? '1er' : `${n}e`
}

/** The cinemas covered by the site, read from Supabase, each with its coverage. */
export function CinemaList({
  load = fetchCinemas,
  now,
}: {
  load?: () => Promise<CinemaWithCoverage[]>
  /** Fixed clock for tests; the current time otherwise. */
  now?: Date
}) {
  const [state, setState] = useState<State>({ status: 'loading' })
  // Load once, even if a parent passes a new function on each render.
  const [loadOnce] = useState(() => load)
  // « il y a … » is computed once per visit, not refreshed live (out of scope for #12).
  const [clock] = useState(() => now ?? new Date())

  useEffect(() => {
    let active = true
    loadOnce().then(
      (cinemas) => active && setState({ status: 'ok', cinemas }),
      () => active && setState({ status: 'error' }),
    )
    return () => {
      active = false
    }
  }, [loadOnce])

  if (state.status === 'loading')
    return <p className="cinema-list__note">on déplie l’affichette…</p>
  if (state.status === 'error') {
    return (
      <p className="hand cinema-list__error">
        (on n’arrive pas à joindre la base, réessaie plus tard)
      </p>
    )
  }
  if (state.cinemas.length === 0) {
    return <p className="hand cinema-list__error">(pas encore de salle ici, reviens bientôt)</p>
  }
  const today = parisDate(clock)
  return (
    <section className="cinema-list" aria-labelledby="cinema-list-title">
      <h2 id="cinema-list-title">les {state.cinemas.length} salles</h2>
      <ul>
        {state.cinemas.map((cinema) => (
          <li key={cinema.id}>
            <span className="cinema-list__name">{cinema.name}</span>
            {cinema.acceptsUgc && <Badge>ugc</Badge>}
            {cinema.arrondissement !== null && (
              <span className="cinema-list__arr">{arrondissementLabel(cinema.arrondissement)}</span>
            )}
            <CoverageLine coverage={cinema} today={today} now={clock} />
          </li>
        ))}
      </ul>
    </section>
  )
}
