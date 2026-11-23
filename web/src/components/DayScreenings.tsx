import { useEffect, useState } from 'react'
import { dayTitle } from '../lib/days'
import { fetchDayScreenings, groupByFilm, type DayFilm } from '../lib/screenings'
import { FilmCard, FilmGrid } from './FilmCard'
import './DayScreenings.css'

type Result = { status: 'error' } | { status: 'ok'; films: DayFilm[] }

async function loadDay(day: string): Promise<DayFilm[]> {
  return groupByFilm(await fetchDayScreenings(day))
}

interface DayScreeningsProps {
  /** Paris calendar day shown (YYYY-MM-DD). */
  day: string
  today: string
  load?: (day: string) => Promise<DayFilm[]>
}

/** Main view: one card per film showing on `day`, with its showtimes grouped by cinema. */
export function DayScreenings({ day, today, load = loadDay }: DayScreeningsProps) {
  // The result remembers its day: a stale one means « loading », with no reset in the effect.
  const [state, setState] = useState<{ day: string; result: Result } | null>(null)
  const [loadOnce] = useState(() => load)

  useEffect(() => {
    let active = true
    loadOnce(day).then(
      (films) => active && setState({ day, result: { status: 'ok', films } }),
      () => active && setState({ day, result: { status: 'error' } }),
    )
    return () => {
      active = false
    }
  }, [loadOnce, day])

  const when = dayTitle(day, today)

  if (!state || state.day !== day)
    return <p className="day-screenings__note">on déplie l’affichette…</p>
  if (state.result.status === 'error') {
    return (
      <p className="hand day-screenings__error">
        (on n’arrive pas à joindre la base, réessaie plus tard)
      </p>
    )
  }
  const { films } = state.result
  if (films.length === 0) {
    return (
      <div className="day-screenings__empty">
        <p>rien de programmé {when} pour l’instant.</p>
        <p className="hand day-screenings__hint">(les salles publient souvent le mercredi)</p>
      </div>
    )
  }
  return (
    <section className="day-screenings" aria-labelledby="day-screenings-title">
      <h2 id="day-screenings-title">
        {films.length} {films.length === 1 ? 'film' : 'films'} {when}
      </h2>
      <FilmGrid>
        {films.map(({ key, ...film }) => (
          <FilmCard key={key} {...film} />
        ))}
      </FilmGrid>
    </section>
  )
}
