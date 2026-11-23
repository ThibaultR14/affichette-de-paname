import { useEffect, useRef } from 'react'
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

/** Horizontal scroll that brings `child` fully inside `container` (0 if it already is). */
function overflow(container: Element, child: Element): number {
  const box = container.getBoundingClientRect()
  const item = child.getBoundingClientRect()
  if (item.left < box.left) return item.left - box.left
  if (item.right > box.right) return Math.min(item.right - box.right, item.left - box.left)
  return 0
}

/** Scrollable strip of the 7 days; the chosen day is underlined in blue pen. */
export function DayStrip({ days, today, selected, onSelect }: DayStripProps) {
  const stripRef = useRef<HTMLElement>(null)
  const selectedRef = useRef<HTMLButtonElement>(null)

  // A shared link to the 7th day must not open with that day hidden off a narrow strip.
  // Only the strip scrolls, horizontally: scrollIntoView would also move the page.
  useEffect(() => {
    const strip = stripRef.current
    const button = selectedRef.current
    if (strip && button) strip.scrollLeft += overflow(strip, button)
  }, [selected])

  return (
    <nav ref={stripRef} className="day-strip" aria-label="jours">
      <ul>
        {days.map((day) => {
          const isSelected = day === selected
          return (
            <li key={day}>
              <button
                type="button"
                ref={isSelected ? selectedRef : undefined}
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
