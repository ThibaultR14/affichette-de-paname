import { coverageStatus, type Coverage } from '../lib/coverage'
import './CoverageLine.css'

/** « programme connu jusqu’au ven. 27 · mis à jour il y a 3 h », plus a note on failure. */
export function CoverageLine({
  coverage,
  today,
  now,
}: {
  coverage: Coverage
  today?: string
  now?: Date
}) {
  const { line, failed } = coverageStatus(coverage, today, now)
  return (
    <div className="coverage">
      {line && <p className="coverage__line">{line}</p>}
      {failed && (
        <p className="hand coverage__failed">
          (on n’a pas pu mettre à jour cette salle aujourd’hui)
        </p>
      )}
    </div>
  )
}
