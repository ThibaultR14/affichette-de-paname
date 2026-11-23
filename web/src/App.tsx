import { CinemaList } from './components/CinemaList'
import { DayScreenings } from './components/DayScreenings'
import { DayStrip } from './components/DayStrip'
import { useSelectedDay } from './lib/dayParam'

export default function App() {
  const { today, week, day, setDay } = useSelectedDay()
  return (
    <main>
      <h1>l'affichette de paname</h1>
      <p>salut. voilà ce qui passe dans les petites salles de paname cette semaine.</p>
      <DayStrip days={week} today={today} selected={day} onSelect={setDay} />
      <DayScreenings day={day} today={today} />
      <CinemaList />
    </main>
  )
}
