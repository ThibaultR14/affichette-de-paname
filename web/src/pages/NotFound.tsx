import { useEffect } from 'react'
import { Link } from '../lib/router'
import './NotFound.css'

const NOTES = {
  film: '(ce film n’est pas sur l’affichette, ou le lien est cassé)',
  page: '(cette page n’existe pas, ou le lien est cassé)',
}

/** Clean 404 (the SPA still answers 200: Pages serves index.html for every path). */
export function NotFound({ what = 'page' }: { what?: 'film' | 'page' }) {
  useEffect(() => {
    const previous = document.title
    document.title = `${what} introuvable · l’affichette de paname`
    return () => {
      document.title = previous
    }
  }, [what])
  return (
    <main className="not-found">
      <h1>{what} introuvable</h1>
      <p className="hand not-found__note">{NOTES[what]}</p>
      <p>
        <Link href="/">retour à l’accueil</Link>
      </p>
    </main>
  )
}
