/** Hand-drawn wavy underline in blue pen (from the Recsys mockup). Decorative. */
export function Squiggle({ className }: { className?: string }) {
  return (
    <svg className={className} aria-hidden="true" viewBox="0 0 300 14" preserveAspectRatio="none">
      <path
        d="M2 9 C 60 3, 120 12, 180 6 S 270 4, 298 8"
        fill="none"
        stroke="var(--color-pen)"
        strokeWidth="3"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
