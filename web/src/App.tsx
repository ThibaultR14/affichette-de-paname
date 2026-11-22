import { useState } from 'react'
import { CinemaList } from './components/CinemaList'
import { rollingWeek } from './lib/days'

export default function App() {
  const [week] = useState(() => rollingWeek(new Date()))
  return (
    <main>
      <h1>l'affichette de paname</h1>
      <p>salut. bientôt ici : ce qui passe dans les petites salles de paname cette semaine.</p>
      <p>
        du {week[0]} au {week[6]}
      </p>
      <CinemaList />
    </main>
  )
}
