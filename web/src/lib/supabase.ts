import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

/**
 * Public client (anon key + RLS). Null when the env vars are missing (misconfigured
 * preview, tests): callers show an error instead of crashing the whole page.
 */
export const supabase: SupabaseClient | null = url && anonKey ? createClient(url, anonKey) : null
