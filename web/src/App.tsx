import { useState } from 'react'
import { CinemaList } from './components/CinemaList'
import { DayScreenings } from './components/DayScreenings'
import { parisDate } from './lib/days'

export default function App() {
  // Day strip and ?jour= come with #9: today for now.
  const [today] = useState(() => parisDate(new Date()))
  return (
    <main>
      <h1>l'affichette de paname</h1>
      <p>salut. voilà ce qui passe dans les petites salles de paname cette semaine.</p>
      <DayScreenings day={today} today={today} />
      <CinemaList />
    </main>
  )
}
