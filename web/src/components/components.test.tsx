import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Badge } from './Badge'
import { Button } from './Button'
import { ActiveFilterChip, Chip } from './Chip'
import { dayLabel } from '../lib/days'
import { DayStrip } from './DayStrip'
import { FilmCard, type CinemaShowtimes } from './FilmCard'
import { ThemeToggle } from './ThemeToggle'

describe('Button', () => {
  it('is a plain button by default', () => {
    render(<Button>ok</Button>)
    expect(screen.getByRole('button', { name: 'ok' })).toHaveAttribute('type', 'button')
  })
})

describe('Chip', () => {
  it('exposes its state and toggles it', () => {
    const onToggle = vi.fn()
    render(
      <Chip pressed={false} onToggle={onToggle}>
        carte ugc
      </Chip>,
    )
    const chip = screen.getByRole('button', { name: 'carte ugc' })
    expect(chip).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(chip)
    expect(onToggle).toHaveBeenCalledWith(true)
  })

  it('active filter chip says what it removes', () => {
    const onRemove = vi.fn()
    render(<ActiveFilterChip label="louxor" onRemove={onRemove} />)
    fireEvent.click(screen.getByRole('button', { name: 'retirer le filtre louxor' }))
    expect(onRemove).toHaveBeenCalled()
  })
})

describe('Badge', () => {
  it('is lowercase', () => {
    render(<Badge>VOSTFR</Badge>)
    expect(screen.getByText('vostfr')).toBeInTheDocument()
  })
})

describe('DayStrip', () => {
  const days = ['2026-11-22', '2026-11-23', '2026-11-24', '2026-11-25']

  it('labels the days and marks the selected one', () => {
    const onSelect = vi.fn()
    render(<DayStrip days={days} today="2026-11-22" selected="2026-11-22" onSelect={onSelect} />)
    const strip = screen.getByRole('navigation', { name: 'jours' })
    const buttons = within(strip).getAllByRole('button')
    expect(buttons.map((b) => b.textContent)).toEqual(['auj.', 'dem.', 'mar. 24', 'mer. 25'])
    expect(buttons[0]).toHaveAttribute('aria-current', 'date')
    expect(buttons[1]).not.toHaveAttribute('aria-current')
    fireEvent.click(buttons[3])
    expect(onSelect).toHaveBeenCalledWith('2026-11-25')
  })

  it('is a row of native buttons, reachable with Tab', () => {
    render(<DayStrip days={days} today="2026-11-22" selected="2026-11-22" />)
    for (const button of screen.getAllByRole('button')) {
      expect(button.tagName).toBe('BUTTON')
      expect(button).toHaveAttribute('type', 'button')
      expect(button).not.toHaveAttribute('tabindex')
    }
  })

  it('scrolls the strip, not the page, to show the selected day', () => {
    // 4 buttons of 80 px in a 200 px wide strip: « mer. 25 » sits at 240-320 px.
    const rect = (left: number, width: number) => ({ left, right: left + width }) as DOMRect
    const spy = vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (
      this: Element,
    ) {
      if (this.tagName === 'NAV') return rect(0, 200)
      const index = days.findIndex((d) => this.textContent === dayLabel(d, '2026-11-22'))
      const scrollLeft = (this.closest('nav') as HTMLElement).scrollLeft
      return rect(index * 80 - scrollLeft, 80)
    })
    const scrollPage = vi.fn()
    const original = Element.prototype.scrollIntoView
    Element.prototype.scrollIntoView = scrollPage
    try {
      const { rerender } = render(<DayStrip days={days} today="2026-11-22" selected="2026-11-25" />)
      const strip = screen.getByRole('navigation', { name: 'jours' })
      expect(strip.scrollLeft).toBe(120)
      rerender(<DayStrip days={days} today="2026-11-22" selected="2026-11-23" />)
      expect(strip.scrollLeft).toBe(80)
      rerender(<DayStrip days={days} today="2026-11-22" selected="2026-11-24" />)
      expect(strip.scrollLeft).toBe(80)
      expect(scrollPage).not.toHaveBeenCalled()
    } finally {
      spy.mockRestore()
      Element.prototype.scrollIntoView = original
    }
  })
})

describe('FilmCard', () => {
  const cinemas: CinemaShowtimes[] = [
    {
      cinemaId: 'champo',
      cinemaName: 'Le Champo',
      acceptsUgc: true,
      showtimes: [
        {
          id: 'champo-1',
          startsAt: '2026-11-26T13:00:00Z',
          version: 'VO',
          format: '35mm',
          bookingUrl: 'https://example.org/resa',
        },
      ],
    },
    {
      cinemaId: 'filmotheque',
      cinemaName: 'Filmothèque du Quartier Latin',
      acceptsUgc: false,
      showtimes: [
        { id: 'filmo-1', startsAt: '2026-11-26T19:30:00Z', bookingUrl: 'https://example.org/prog' },
      ],
    },
  ]

  it('shows title, meta, and showtimes with end time in Paris time', () => {
    render(
      <FilmCard
        tmdbId={266}
        title="Le Mépris"
        directors={['Jean-Luc Godard']}
        year={1963}
        runtimeMin={103}
        posterUrl="data:image/png;base64,"
        cinemas={cinemas}
      />,
    )
    expect(screen.getByRole('heading', { name: 'Le Mépris' })).toBeInTheDocument()
    expect(screen.getByText('Jean-Luc Godard, 1963 · 1 h 43')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /14:00 → 15:43/ })
    expect(link).toHaveAttribute('href', 'https://example.org/resa')
    expect(link).toHaveTextContent('vo')
    expect(link).toHaveTextContent('35mm')
    expect(screen.getByRole('link', { name: /20:30 → 22:13/ })).toHaveAttribute(
      'href',
      'https://example.org/prog',
    )
    expect(screen.queryByText(/on n'a pas trouvé/)).not.toBeInTheDocument()
  })

  it('links the title of a matched film to its page, in place', () => {
    render(<FilmCard tmdbId={266} href="/film/266" title="Le Mépris" cinemas={cinemas} />)
    const title = screen.getByRole('link', { name: 'Le Mépris' })
    expect(title).toHaveAttribute('href', '/film/266')
    expect(title).not.toHaveAttribute('target')
    fireEvent.click(title)
    expect(window.location.pathname).toBe('/film/266')
    window.history.replaceState(null, '', '/')
  })

  it('keeps a plain title without href (styleguide), or without TMDB match', () => {
    render(<FilmCard tmdbId={266} title="Le Mépris" cinemas={cinemas} />)
    expect(screen.queryByRole('link', { name: 'Le Mépris' })).toBeNull()
  })

  it('puts the ugc badge next to UGC cinemas only', () => {
    render(<FilmCard tmdbId={1} title="x" cinemas={cinemas} />)
    expect(screen.getByText('Le Champo').parentElement).toHaveTextContent('ugc')
    expect(screen.getByText('Filmothèque du Quartier Latin').parentElement).not.toHaveTextContent(
      'ugc',
    )
  })

  it('hides the end time when the runtime is unknown', () => {
    render(<FilmCard tmdbId={1} title="x" year={1967} cinemas={cinemas} />)
    const link = screen.getByRole('link', { name: /14:00/ })
    expect(link).not.toHaveTextContent('→')
    expect(screen.getByText('1967')).toBeInTheDocument()
  })

  it('shows the time as plain text when there is no link to give', () => {
    const noLink: CinemaShowtimes[] = [
      {
        cinemaId: 'louxor',
        cinemaName: 'Le Louxor',
        acceptsUgc: true,
        showtimes: [{ id: 'l-1', startsAt: '2026-11-26T13:00:00Z', bookingUrl: null }],
      },
    ]
    render(<FilmCard tmdbId={1} title="x" cinemas={noLink} />)
    expect(screen.queryByRole('link', { name: /14:00/ })).toBeNull()
    expect(screen.getByText('14:00')).toBeInTheDocument()
  })

  it('without a TMDB match: no poster, apology note', () => {
    const { container } = render(
      <FilmCard tmdbId={null} title="Nuit des courts" cinemas={cinemas} />,
    )
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('.film-card__poster--none')).not.toBeNull()
    expect(screen.getByText("(on n'a pas trouvé ce film, désolé)")).toBeInTheDocument()
  })

  it('shows the favourite button only when the state is known', () => {
    const { rerender } = render(<FilmCard tmdbId={1} title="Le Mépris" cinemas={[]} />)
    expect(screen.queryByRole('button')).toBeNull()
    const onToggle = vi.fn()
    rerender(
      <FilmCard tmdbId={1} title="Le Mépris" cinemas={[]} favorite onToggleFavorite={onToggle} />,
    )
    const fav = screen.getByRole('button', { name: 'retirer Le Mépris des favoris' })
    expect(fav).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(fav)
    expect(onToggle).toHaveBeenCalled()
  })

  it('no favourite button without a TMDB match (favourites are TMDB films)', () => {
    render(<FilmCard tmdbId={null} title="Nuit des courts" cinemas={[]} favorite={false} />)
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('accepts two screenings at the same time (different ids)', () => {
    const twin: CinemaShowtimes = {
      cinemaId: 'louxor',
      cinemaName: 'Le Louxor',
      acceptsUgc: true,
      showtimes: [
        { id: 'a', startsAt: '2026-11-26T20:00:00Z', version: 'vo', bookingUrl: 'https://e.org/a' },
        { id: 'b', startsAt: '2026-11-26T20:00:00Z', version: 'vf', bookingUrl: 'https://e.org/b' },
      ],
    }
    render(<FilmCard tmdbId={1} title="x" cinemas={[twin]} />)
    expect(screen.getAllByRole('link', { name: /21:00/ })).toHaveLength(2)
  })

  it('clamps the tilt to ±1.8°', () => {
    const { container } = render(<FilmCard tmdbId={1} title="x" cinemas={[]} tilt={7} />)
    expect(container.querySelector('article')?.style.getPropertyValue('--tilt')).toBe('1.8deg')
  })
})

describe('ThemeToggle', () => {
  it('says what it does and switches the theme', () => {
    document.documentElement.dataset.theme = 'light'
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: 'passer en sombre' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(screen.getByRole('button', { name: 'passer en clair' })).toBeInTheDocument()
    delete document.documentElement.dataset.theme
    localStorage.clear()
  })
})
