import { parisTime } from '../lib/days'
import { Badge } from './Badge'
import type { CinemaShowtimes } from './FilmCard'
import './ShowtimeList.css'

function endTime(startsAt: string, runtimeMin?: number | null): string | null {
  if (!runtimeMin) return null
  return parisTime(new Date(new Date(startsAt).getTime() + runtimeMin * 60_000))
}

/**
 * Showtimes grouped by cinema: cinema name (ugc badge), then « 14:00 → 15:43 » with its badges,
 * each a link to the booking page when one is known. The end time needs the runtime.
 */
export function ShowtimeList({
  cinemas,
  runtimeMin,
  className,
}: {
  cinemas: CinemaShowtimes[]
  runtimeMin?: number | null
  className?: string
}) {
  return (
    <ul className={className ? `showtimes ${className}` : 'showtimes'}>
      {cinemas.map((cinema) => (
        <li key={cinema.cinemaId}>
          <p className="showtimes__cinema">
            <span>{cinema.cinemaName}</span>
            {cinema.acceptsUgc && <Badge>ugc</Badge>}
          </p>
          <ul className="showtimes__times">
            {cinema.showtimes.map((s) => {
              const end = endTime(s.startsAt, runtimeMin)
              const content = (
                <>
                  <span className="showtime__hours">
                    <time dateTime={s.startsAt}>{parisTime(new Date(s.startsAt))}</time>
                    {end && <> → {end}</>}
                  </span>
                  {s.version && <Badge>{s.version}</Badge>}
                  {s.format && <Badge>{s.format}</Badge>}
                </>
              )
              return (
                <li key={s.id}>
                  {s.bookingUrl ? (
                    <a
                      className="showtime"
                      href={s.bookingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {content}
                    </a>
                  ) : (
                    <span className="showtime showtime--nolink">{content}</span>
                  )}
                </li>
              )
            })}
          </ul>
        </li>
      ))}
    </ul>
  )
}
