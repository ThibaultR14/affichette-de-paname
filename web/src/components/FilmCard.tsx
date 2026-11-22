import type { CSSProperties, ReactNode } from 'react'
import { formatRuntime, parisTime } from '../lib/days'
import { Badge } from './Badge'
import './FilmCard.css'

export interface Showtime {
  /** Stable id of the screening (screenings.source_key): two can share a start time. */
  id: string
  /** UTC instant (ISO 8601), shown in Paris time. */
  startsAt: string
  version?: string | null
  format?: string | null
  /** Booking page, or the cinema's programme page when there is none. */
  bookingUrl: string
}

export interface CinemaShowtimes {
  cinemaId: string
  cinemaName: string
  acceptsUgc: boolean
  showtimes: Showtime[]
}

export interface FilmCardProps {
  /** null when the screening has no TMDB match: no poster, title as given by the cinema. */
  tmdbId: number | null
  title: string
  directors?: string[]
  year?: number | null
  runtimeMin?: number | null
  posterUrl?: string | null
  cinemas: CinemaShowtimes[]
  /** Shown only when defined (signed-in user). */
  favorite?: boolean
  onToggleFavorite?: () => void
  /** Rotation of the taped photo on wide screens, ±1.8° at most. */
  tilt?: number
}

const MAX_TILT = 1.8

function metaLine(directors: string[], year?: number | null, runtimeMin?: number | null) {
  const who = [directors.join(' et '), year].filter(Boolean).join(', ')
  return [who, runtimeMin ? formatRuntime(runtimeMin) : null].filter(Boolean).join(' · ') // the runtime never starts a line
}

function endTime(startsAt: string, runtimeMin?: number | null): string | null {
  if (!runtimeMin) return null
  return parisTime(new Date(new Date(startsAt).getTime() + runtimeMin * 60_000))
}

/** Film card (« taped photo »), static: poster, title, meta, the day's showtimes by cinema. */
export function FilmCard({
  tmdbId,
  title,
  directors = [],
  year,
  runtimeMin,
  posterUrl,
  cinemas,
  favorite,
  onToggleFavorite,
  tilt = 0,
}: FilmCardProps) {
  const matched = tmdbId !== null
  const meta = matched ? metaLine(directors, year, runtimeMin) : ''
  const clampedTilt = Math.max(-MAX_TILT, Math.min(MAX_TILT, tilt))

  return (
    <article className="film-card" style={{ '--tilt': `${clampedTilt}deg` } as CSSProperties}>
      <div
        className={posterUrl ? 'film-card__poster' : 'film-card__poster film-card__poster--none'}
      >
        <span className="tape" aria-hidden="true" />
        {posterUrl && <img src={posterUrl} alt="" loading="lazy" />}
      </div>

      <header className="film-card__header">
        <h3 className="film-card__title">{title}</h3>
        {meta && <p className="film-card__meta">{meta}</p>}
        {!matched && <p className="hand film-card__missing">(on n'a pas trouvé ce film, désolé)</p>}
      </header>

      {matched && favorite !== undefined && (
        <button
          type="button"
          className="film-card__favorite"
          aria-pressed={favorite}
          aria-label={favorite ? `retirer ${title} des favoris` : `ajouter ${title} aux favoris`}
          onClick={onToggleFavorite}
        >
          <span aria-hidden="true">✱</span>
          <svg aria-hidden="true" viewBox="0 0 24 22" width="22" height="20">
            <path
              d="M12 20 C 4 14, 1 10, 2 6 C 3 2, 8 1, 12 5 C 16 1, 21 2, 22 6 C 23 10, 20 14, 12 20 Z"
              fill={favorite ? 'currentColor' : 'none'}
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      )}

      <ul className="film-card__cinemas">
        {cinemas.map((cinema) => (
          <li key={cinema.cinemaId}>
            <p className="film-card__cinema">
              <span>{cinema.cinemaName}</span>
              {cinema.acceptsUgc && <Badge>ugc</Badge>}
            </p>
            <ul className="film-card__times">
              {cinema.showtimes.map((s) => {
                const end = endTime(s.startsAt, runtimeMin)
                return (
                  <li key={s.id}>
                    <a
                      className="showtime"
                      href={s.bookingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <span className="showtime__hours">
                        <time dateTime={s.startsAt}>{parisTime(new Date(s.startsAt))}</time>
                        {end && <> → {end}</>}
                      </span>
                      {s.version && <Badge>{s.version}</Badge>}
                      {s.format && <Badge>{s.format}</Badge>}
                    </a>
                  </li>
                )
              })}
            </ul>
          </li>
        ))}
      </ul>
    </article>
  )
}

/** Responsive grid of film cards: one column of compact rows on mobile, photos from 640 px. */
export function FilmGrid({ children }: { children: ReactNode }) {
  return <div className="film-grid">{children}</div>
}
