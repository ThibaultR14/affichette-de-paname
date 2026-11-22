import { useState } from 'react'
import { applyTheme, currentTheme, type Theme } from '../lib/theme'

/** « passer en sombre » / « passer en clair »: the label says what the button does. No emoji. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(currentTheme)
  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      className="link-button"
      onClick={() => {
        applyTheme(next)
        setTheme(next)
      }}
    >
      {next === 'dark' ? 'passer en sombre' : 'passer en clair'}
    </button>
  )
}
