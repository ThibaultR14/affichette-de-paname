import './Badge.css'

/** Screening badge (« vo », « 35mm », « ugc »): ink border, no fill, no extra colour. */
export function Badge({ children }: { children: string }) {
  return <span className="badge">{children.toLowerCase()}</span>
}
