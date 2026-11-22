import type { ButtonHTMLAttributes } from 'react'
import './Button.css'

/** Main button (docs/design.md): surface, 2 px ink border, 48 px high, bold 16 px. */
export function Button({
  className,
  type = 'button',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type={type} className={className ? `button ${className}` : 'button'} {...props} />
}
