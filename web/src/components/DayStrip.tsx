import { dayLabel } from '../lib/days'
import { Squiggle } from './Squiggle'
import './DayStrip.css'

interface DayStripProps {
  /** Paris calendar dates (YYYY-MM-DD), today first: rollingWeek(). */
  days: string[]
  today: string
  selected: string
  onSelect?: (day: string) => void
}

/** Scrollable strip of the 7 days; the chosen day is underlined in blue pen. */
export function DayStrip({ days, today, selected, onSelect }: DayStripProps) {
  return (
    <nav className="day-strip" aria-label="jours">
      <ul>
        {days.map((day) => {
          const isSelected = day === selected
          return (
            <li key={day}>
              <button
                type="button"
                className="day-strip__day"
                aria-current={isSelected ? 'date' : undefined}
                onClick={() => onSelect?.(day)}
              >
                <span className="day-strip__label">
                  {dayLabel(day, today)}
                  {isSelected && <Squiggle className="day-strip__squiggle" />}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
