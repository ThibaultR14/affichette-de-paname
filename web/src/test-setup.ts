import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest globals are off, so Testing Library does not unmount by itself between tests.
afterEach(cleanup)

// jsdom does not implement scrolling; Link scrolls to the top after navigating.
if (typeof window !== 'undefined') window.scrollTo = () => {}
