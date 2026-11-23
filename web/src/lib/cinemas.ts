import type { SupabaseClient } from '@supabase/supabase-js'
import type { Coverage } from './coverage'
import { supabase } from './supabase'

export type Cinema = {
  id: string
  name: string
  arrondissement: number | null
  acceptsUgc: boolean
}

/** A cinema as read by `fetchCinemas`, with what the import knows of its programme. */
export type CinemaWithCoverage = Cinema & Coverage

export type CinemasClient = Pick<SupabaseClient, 'from'>

type CinemaRow = {
  id: string
  name: string
  arrondissement: number | null
  accepts_ugc: boolean
  coverage_until: string | null
  last_success_at: string | null
  last_import_ok: boolean | null
}

export async function fetchCinemas(
  client: CinemasClient | null = supabase,
): Promise<CinemaWithCoverage[]> {
  if (!client) {
    throw new Error('Supabase is not configured (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY)')
  }
  const { data, error } = await client
    .from('cinemas')
    .select(
      'id, name, arrondissement, accepts_ugc, coverage_until, last_success_at, last_import_ok',
    )
    .order('name')
  if (error) throw new Error(error.message)
  return (data as CinemaRow[]).map((row) => ({
    id: row.id,
    name: row.name,
    arrondissement: row.arrondissement,
    acceptsUgc: row.accepts_ugc,
    coverageUntil: row.coverage_until,
    lastSuccessAt: row.last_success_at,
    lastImportOk: row.last_import_ok,
  }))
}
