import { useId, useState } from 'react'
import type { Cinema } from '../lib/cinemas'
import { NO_FILTERS, hasActiveFilters, type Filters } from '../lib/filters'
import { ActiveFilterChip, Chip } from './Chip'
import './FilterPanel.css'

interface FilterPanelProps {
  cinemas: Cinema[]
  filters: Filters
  onChange: (filters: Filters) => void
}

const HERITAGE_LABEL = 'patrimoine (+ de 20 ans)'
const UGC_LABEL = 'carte ugc'

const lower = (name: string) => name.toLocaleLowerCase('fr')

/** « affiner » button, folding panel of toggle chips, and the active filters as « × » chips. */
export function FilterPanel({ cinemas, filters, onChange }: FilterPanelProps) {
  const [open, setOpen] = useState(false)
  const panelId = useId()

  const sorted = [...cinemas].sort((a, b) =>
    a.name.localeCompare(b.name, 'fr', { sensitivity: 'base' }),
  )
  const nameOf = (id: string) => {
    const cinema = cinemas.find((c) => c.id === id)
    return cinema ? lower(cinema.name) : id
  }
  const withCinema = (id: string, on: boolean) =>
    on ? [...filters.cinemas, id] : filters.cinemas.filter((c) => c !== id)

  return (
    <div className="filter-panel">
      <button
        type="button"
        className="filter-panel__toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(!open)}
      >
        affiner <span aria-hidden="true">{open ? '▴' : '▾'}</span>
      </button>

      <div id={panelId} className="filter-panel__panel" hidden={!open}>
        {open && (
          <>
            <div className="filter-panel__row">
              <Chip
                pressed={filters.heritage}
                onToggle={(heritage) => onChange({ ...filters, heritage })}
              >
                {HERITAGE_LABEL}
              </Chip>
              <Chip pressed={filters.ugc} onToggle={(ugc) => onChange({ ...filters, ugc })}>
                {UGC_LABEL}
              </Chip>
            </div>
            <div className="filter-panel__row" role="group" aria-label="salles">
              {sorted.map((cinema) => (
                <Chip
                  key={cinema.id}
                  pressed={filters.cinemas.includes(cinema.id)}
                  onToggle={(on) => onChange({ ...filters, cinemas: withCinema(cinema.id, on) })}
                >
                  {lower(cinema.name)}
                </Chip>
              ))}
            </div>
          </>
        )}
      </div>

      {hasActiveFilters(filters) && (
        <div className="filter-panel__row filter-panel__active">
          {filters.heritage && (
            <ActiveFilterChip
              label="patrimoine"
              onRemove={() => onChange({ ...filters, heritage: false })}
            />
          )}
          {filters.ugc && (
            <ActiveFilterChip
              label={UGC_LABEL}
              onRemove={() => onChange({ ...filters, ugc: false })}
            />
          )}
          {filters.cinemas.map((id) => (
            <ActiveFilterChip
              key={id}
              label={nameOf(id)}
              onRemove={() => onChange({ ...filters, cinemas: withCinema(id, false) })}
            />
          ))}
          <button type="button" className="link-button" onClick={() => onChange(NO_FILTERS)}>
            tout effacer
          </button>
        </div>
      )}
    </div>
  )
}
