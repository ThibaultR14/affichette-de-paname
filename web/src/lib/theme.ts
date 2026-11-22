/**
 * Theme (docs/design.md): follows the system preference, light when there is none. The toggle's
 * choice is the only thing stored in the browser. index.html applies it before the first paint,
 * with the same key and rule as `initialTheme` below.
 */
export type Theme = 'light' | 'dark'

export const THEME_KEY = 'affichette-theme'

function storedTheme(): Theme | null {
  try {
    const v = localStorage.getItem(THEME_KEY)
    return v === 'light' || v === 'dark' ? v : null
  } catch {
    return null
  }
}

/** Stored choice, else the system preference, else light. */
export function initialTheme(): Theme {
  const stored = storedTheme()
  if (stored) return stored
  return typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function currentTheme(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(THEME_KEY, theme)
  } catch {
    // private browsing or blocked storage: the theme works, it is just not remembered
  }
}
