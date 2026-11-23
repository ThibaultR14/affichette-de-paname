import { useEffect, useState } from 'react'
import { CinemaList } from './components/CinemaList'
import { DayScreenings } from './components/DayScreenings'
import { DayStrip } from './components/DayStrip'
import { FilterPanel } from './components/FilterPanel'
import { fetchCinemas, type Cinema } from './lib/cinemas'
import { useSelectedDay } from './lib/dayParam'
import { NO_FILTERS, useFilters } from './lib/filters'

export default function App() {
  const { today, week, day, setDay } = useSelectedDay()
  const { filters, setFilters } = useFilters()
  // null until loaded: the panel then shows cinema ids as they are in the URL.
  const [cinemas, setCinemas] = useState<Cinema[] | null>(null)

  useEffect(() => {
    let active = true
    fetchCinemas().then(
      (list) => active && setCinemas(list),
      () => {}, // CinemaList shows the error; the panel just has no cinema chips.
    )
    return () => {
      active = false
    }
  }, [])

  // Ids from a shared link that are not (or no longer) cinemas are dropped from the URL.
  useEffect(() => {
    // An empty list means a broken read (RLS, empty table), not that every id is wrong.
    if (!cinemas?.length) return
    const known = filters.cinemas.filter((id) => cinemas.some((c) => c.id === id))
    if (known.length !== filters.cinemas.length) setFilters({ ...filters, cinemas: known })
  }, [cinemas, filters, setFilters])

  return (
    <main>
      <h1>l'affichette de paname</h1>
      <p>salut. voilà ce qui passe dans les petites salles de paname cette semaine.</p>
      <DayStrip days={week} today={today} selected={day} onSelect={setDay} />
      <FilterPanel cinemas={cinemas ?? []} filters={filters} onChange={setFilters} />
      <DayScreenings
        day={day}
        today={today}
        filters={filters}
        onClearFilters={() => setFilters(NO_FILTERS)}
      />
      <CinemaList />
    </main>
  )
}
