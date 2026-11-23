import { useState, type ReactNode } from 'react'
import { ActiveFilterChip, Chip } from '../components/Chip'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { DayStrip } from '../components/DayStrip'
import { FilmCard, FilmGrid, type FilmCardProps } from '../components/FilmCard'
import { CoverageLine } from '../components/CoverageLine'
import { ThemeToggle } from '../components/ThemeToggle'
import { parisDate, rollingWeek } from '../lib/days'
import './Styleguide.css'

const TOKENS = ['paper', 'surface', 'ink', 'muted', 'rule', 'pen'] as const

/** Flat coloured poster, no network (the real ones come from image.tmdb.org). */
function fakePoster(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2 3"><rect width="2" height="3" fill="${color}"/></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

const programme = 'https://example.org/programme'

const FILMS: (FilmCardProps & { key: string })[] = [
  {
    key: 'mepris',
    tmdbId: 266,
    title: 'Le Mépris',
    directors: ['Jean-Luc Godard'],
    year: 1963,
    runtimeMin: 103,
    posterUrl: fakePoster('#24527A'),
    favorite: true,
    tilt: -1.6,
    cinemas: [
      {
        cinemaId: 'champo',
        cinemaName: 'Le Champo',
        acceptsUgc: true,
        showtimes: [
          {
            id: 'demo-0',
            startsAt: '2026-11-26T13:00:00Z',
            version: 'vo',
            format: '35mm',
            bookingUrl: programme,
          },
          { id: 'demo-1', startsAt: '2026-11-26T19:30:00Z', version: 'vo', bookingUrl: programme },
        ],
      },
      {
        cinemaId: 'filmotheque',
        cinemaName: 'Filmothèque du Quartier Latin',
        acceptsUgc: false,
        showtimes: [
          { id: 'demo-2', startsAt: '2026-11-26T20:45:00Z', version: 'vo', bookingUrl: programme },
        ],
      },
    ],
  },
  {
    key: 'samourai',
    tmdbId: 5511,
    title: 'Le Samouraï',
    directors: ['Jean-Pierre Melville'],
    year: 1967,
    runtimeMin: null,
    posterUrl: fakePoster('#7A2E2E'),
    favorite: false,
    tilt: 1.1,
    cinemas: [
      {
        cinemaId: 'grand-action',
        cinemaName: 'Le Grand Action',
        acceptsUgc: true,
        showtimes: [
          { id: 'demo-3', startsAt: '2026-11-26T17:15:00Z', format: '4k', bookingUrl: programme },
        ],
      },
    ],
  },
  {
    key: 'nuit-courts',
    tmdbId: null,
    title: 'Nuit des courts : surprises',
    tilt: -0.6,
    cinemas: [
      {
        cinemaId: 'louxor',
        cinemaName: 'Le Louxor',
        acceptsUgc: true,
        showtimes: [{ id: 'demo-4', startsAt: '2026-11-26T21:00:00Z', bookingUrl: programme }],
      },
    ],
  },
]

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="styleguide__section">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

/** /styleguide: every token and base component, in the current theme. Fake data. */
export default function Styleguide() {
  const [now] = useState(() => new Date())
  const today = parisDate(now)
  const week = rollingWeek(now)
  const [day, setDay] = useState(today)
  const [pressed, setPressed] = useState<Record<string, boolean>>({
    'patrimoine (+ de 20 ans)': true,
  })
  const toggle = (k: string) => (v: boolean) => setPressed((p) => ({ ...p, [k]: v }))

  return (
    <main className="styleguide">
      <header className="styleguide__header">
        <h1>styleguide</h1>
        <ThemeToggle />
      </header>

      <Section title="couleurs">
        <ul className="styleguide__swatches">
          {TOKENS.map((t) => (
            <li key={t}>
              <span className="styleguide__swatch" style={{ background: `var(--color-${t})` }} />
              <code>{t}</code>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="typo">
        <p className="styleguide__big">
          salut. voilà ce qui passe dans les petites salles de paname.
        </p>
        <p>
          texte courant en courier prime. <strong>gras pour les titres de film.</strong>{' '}
          <span className="styleguide__muted">jean-luc godard, 1963 · 1 h 43</span>
        </p>
        <p className="styleguide__times">14:00 → 15:43 · 20:30 → 22:13</p>
        <p className="hand styleguide__hand">(t'as vu, c'est écrit au stylo)</p>
        <p>
          <a href="#liens">un lien souligné</a>, bleu au survol.
        </p>
      </Section>

      <Section title="boutons">
        <div className="styleguide__row">
          <Button>m'envoyer le lien</Button>
          <Button disabled>désactivé</Button>
        </div>
      </Section>

      <Section title="puces">
        <div className="styleguide__row">
          {['patrimoine (+ de 20 ans)', 'carte ugc', 'le champo', 'le louxor'].map((label) => (
            <Chip key={label} pressed={!!pressed[label]} onToggle={toggle(label)}>
              {label}
            </Chip>
          ))}
        </div>
        <div className="styleguide__row">
          <ActiveFilterChip label="louxor" />
          <ActiveFilterChip label="carte ugc" />
          <button type="button" className="link-button">
            tout effacer
          </button>
        </div>
      </Section>

      <Section title="pastilles">
        <div className="styleguide__row">
          {['vo', 'vf', '35mm', '70mm', '4k', 'ugc'].map((b) => (
            <Badge key={b}>{b}</Badge>
          ))}
        </div>
      </Section>

      <Section title="bandeau des 7 jours">
        <DayStrip days={week} today={today} selected={day} onSelect={setDay} />
      </Section>

      <Section title="couverture d'une salle">
        {[
          { name: 'Le Champo', ok: true, hours: 3 },
          { name: 'Le Louxor', ok: false, hours: 51 },
        ].map(({ name, ok, hours }) => (
          <div key={name} className="styleguide__coverage">
            <strong>{name}</strong>
            <CoverageLine
              coverage={{
                coverageUntil: week[4],
                lastSuccessAt: new Date(now.getTime() - hours * 3_600_000).toISOString(),
                lastImportOk: ok,
              }}
              today={today}
              now={now}
            />
          </div>
        ))}
      </Section>

      <Section title="cartes film">
        <FilmGrid>
          {FILMS.map(({ key, ...film }) => (
            <FilmCard key={key} {...film} />
          ))}
        </FilmGrid>
      </Section>
    </main>
  )
}
