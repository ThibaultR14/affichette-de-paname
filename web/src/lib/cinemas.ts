import type { SupabaseClient } from '@supabase/supabase-js'
import { supabase } from './supabase'

export type Cinema = {
  id: string
  name: string
  arrondissement: number | null
  acceptsUgc: boolean
}

export type CinemasClient = Pick<SupabaseClient, 'from'>

type CinemaRow = {
  id: string
  name: string
  arrondissement: number | null
  accepts_ugc: boolean
}

export async function fetchCinemas(client: CinemasClient | null = supabase): Promise<Cinema[]> {
  if (!client) {
    throw new Error('Supabase is not configured (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY)')
  }
  const { data, error } = await client
    .from('cinemas')
    .select('id, name, arrondissement, accepts_ugc')
    .order('name')
  if (error) throw new Error(error.message)
  return (data as CinemaRow[]).map((row) => ({
    id: row.id,
    name: row.name,
    arrondissement: row.arrondissement,
    acceptsUgc: row.accepts_ugc,
  }))
}
