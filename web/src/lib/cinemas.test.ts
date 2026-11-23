import { describe, expect, it, vi } from 'vitest'
import { fetchCinemas, type CinemasClient } from './cinemas'

function fakeClient(result: { data: unknown; error: { message: string } | null }) {
  const order = vi.fn().mockResolvedValue(result)
  const select = vi.fn(() => ({ order }))
  const from = vi.fn(() => ({ select }))
  return { client: { from } as unknown as CinemasClient, from, select, order }
}

describe('fetchCinemas', () => {
  it('reads the cinemas sorted by name', async () => {
    const rows = [
      {
        id: 'champo',
        name: 'Le Champo',
        arrondissement: 5,
        accepts_ugc: true,
        coverage_until: '2026-11-28',
        last_success_at: '2026-11-23T04:00:00+00:00',
        last_import_ok: true,
      },
    ]
    const { client, from, select, order } = fakeClient({ data: rows, error: null })
    await expect(fetchCinemas(client)).resolves.toEqual([
      {
        id: 'champo',
        name: 'Le Champo',
        arrondissement: 5,
        acceptsUgc: true,
        coverageUntil: '2026-11-28',
        lastSuccessAt: '2026-11-23T04:00:00+00:00',
        lastImportOk: true,
      },
    ])
    expect(from).toHaveBeenCalledWith('cinemas')
    expect(select).toHaveBeenCalledWith(
      'id, name, arrondissement, accepts_ugc, coverage_until, last_success_at, last_import_ok',
    )
    expect(order).toHaveBeenCalledWith('name')
  })

  it('throws when Supabase returns an error', async () => {
    const { client } = fakeClient({ data: null, error: { message: 'boom' } })
    await expect(fetchCinemas(client)).rejects.toThrow('boom')
  })

  it('throws a clear error when Supabase is not configured', async () => {
    await expect(fetchCinemas(null)).rejects.toThrow(/VITE_SUPABASE_URL/)
  })
})
