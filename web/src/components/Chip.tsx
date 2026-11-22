import type { ReactNode } from 'react'
import './Chip.css'

interface ChipProps {
  children: ReactNode
  pressed: boolean
  onToggle?: (pressed: boolean) => void
}

/** Toggle chip of the filter panel: pressed = solid ink, paper text. */
export function Chip({ children, pressed, onToggle }: ChipProps) {
  return (
    <button
      type="button"
      className="chip"
      aria-pressed={pressed}
      onClick={() => onToggle?.(!pressed)}
    >
      {children}
    </button>
  )
}

interface ActiveFilterChipProps {
  label: string
  onRemove?: () => void
}

/** Active filter, dashed: « × louxor ». */
export function ActiveFilterChip({ label, onRemove }: ActiveFilterChipProps) {
  return (
    <button
      type="button"
      className="chip chip--active-filter"
      aria-label={`retirer le filtre ${label}`}
      onClick={onRemove}
    >
      <span aria-hidden="true">×</span> {label}
    </button>
  )
}
