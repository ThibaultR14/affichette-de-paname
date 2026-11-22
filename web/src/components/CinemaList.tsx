import { useEffect, useState } from 'react'
import { fetchCinemas, type Cinema } from '../lib/cinemas'
import { Badge } from './Badge'
import './CinemaList.css'

type State = { status: 'loading' } | { status: 'error' } | { status: 'ok'; cinemas: Cinema[] }

function arrondissementLabel(n: number) {
  return n === 1 ? '1er' : `${n}e`
}

/** The cinemas covered by the site, read from Supabase. */
export function CinemaList({ load = fetchCinemas }: { load?: () => Promise<Cinema[]> }) {
  const [state, setState] = useState<State>({ status: 'loading' })
  // Load once, even if a parent passes a new function on each render.
  const [loadOnce] = useState(() => load)

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
          </li>
        ))}
      </ul>
    </section>
  )
}
