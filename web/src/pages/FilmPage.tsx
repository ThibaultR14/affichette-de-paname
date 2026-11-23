import { useEffect, useState, type MouseEvent } from 'react'
import { ShowtimeList } from '../components/ShowtimeList'
import { dayTitle, parisDate } from '../lib/days'
import { metaLine } from '../lib/filmMeta'
import { fetchFilm, fetchFilmScreenings, groupByDay, type Film, type FilmDay } from '../lib/films'
import { Link, cameFromSite } from '../lib/router'
import { NotFound } from './NotFound'
import './FilmPage.css'

export type FilmPageData = { film: Film; days: FilmDay[] }

/** The film and its week of showtimes; null when the film is not in the base. */
async function loadFilm(tmdbId: number): Promise<FilmPageData | null> {
  const [film, rows] = await Promise.all([fetchFilm(tmdbId), fetchFilmScreenings(tmdbId)])
  return film && { film, days: groupByDay(rows) }
}

type Result = { status: 'error' } | { status: 'ok'; data: FilmPageData | null }

const SITE = 'l’affichette de paname'

/** « ← toutes les séances »: back in history from the site (keeps day and filters), else home. */
function BackLink() {
  const onClick = (e: MouseEvent<HTMLAnchorElement>) => {
    if (!cameFromSite() || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    e.preventDefault()
    window.history.back()
  }
  return (
    <Link href="/" className="film-page__back" onClick={onClick}>
      ← toutes les séances
    </Link>
  )
}

interface FilmPageProps {
  tmdbId: number
  /** Paris calendar day, for the day titles (« aujourd’hui », « demain »…). */
  today?: string
  load?: (tmdbId: number) => Promise<FilmPageData | null>
}

/** Film page: TMDB card and every showtime of the 7-day window, all cinemas, no filters. */
export function FilmPage({ tmdbId, today: todayProp, load = loadFilm }: FilmPageProps) {
  const [state, setState] = useState<{ tmdbId: number; result: Result } | null>(null)
  const [loadOnce] = useState(() => load)
  const [openedOn] = useState(() => parisDate(new Date()))
  const today = todayProp ?? openedOn

  useEffect(() => {
    let active = true
    loadOnce(tmdbId).then(
      (data) => active && setState({ tmdbId, result: { status: 'ok', data } }),
      () => active && setState({ tmdbId, result: { status: 'error' } }),
    )
    return () => {
      active = false
    }
  }, [loadOnce, tmdbId])

  const film = state?.result.status === 'ok' ? state.result.data?.film : undefined
  useEffect(() => {
    if (!film) return
    const previous = document.title
    document.title = `${film.title} · ${SITE}`
    return () => {
      document.title = previous
    }
  }, [film])

  if (!state || state.tmdbId !== tmdbId) {
    return (
      <main>
        <p className="film-page__note">on déplie l’affichette…</p>
      </main>
    )
  }
  if (state.result.status === 'error') {
    return (
      <main>
        <BackLink />
        <p className="hand film-page__error">
          (on n’arrive pas à joindre la base, réessaie plus tard)
        </p>
      </main>
    )
  }
  if (!state.result.data) return <NotFound what="film" />

  const { film: f, days } = state.result.data
  const meta = metaLine(f.directors, f.year, f.runtimeMin)
  const original = f.originalTitle && f.originalTitle !== f.title ? f.originalTitle : null

  return (
    <main className="film-page">
      <BackLink />
      <article className="film-page__card">
        <div
          className={
            f.posterUrl ? 'film-page__poster' : 'film-page__poster film-page__poster--none'
          }
        >
          <span className="tape" aria-hidden="true" />
          {f.posterUrl && <img src={f.posterUrl} alt={`affiche de ${f.title}`} />}
        </div>
        <header className="film-page__header">
          <h1>{f.title}</h1>
          {original && (
            <p className="film-page__original">
              <span className="visually-hidden">titre original : </span>
              <i>{original}</i>
            </p>
          )}
          {meta && <p className="film-page__meta">{meta}</p>}
        </header>
        {f.overview ? (
          <p className="film-page__overview">{f.overview}</p>
        ) : (
          <p className="hand film-page__no-overview">(pas de synopsis en français sur tmdb)</p>
        )}

        <section className="film-page__week" aria-labelledby="film-page-week">
          <h2 id="film-page-week">les séances de la semaine</h2>
          {days.length === 0 ? (
            <p>pas de séance dans les 7 prochains jours.</p>
          ) : (
            days.map(({ day, cinemas }) => (
              <section key={day} className="film-page__day" aria-labelledby={`jour-${day}`}>
                <h3 id={`jour-${day}`}>{dayTitle(day, today)}</h3>
                <ShowtimeList cinemas={cinemas} runtimeMin={f.runtimeMin} />
              </section>
            ))
          )}
        </section>
      </article>
    </main>
  )
}
