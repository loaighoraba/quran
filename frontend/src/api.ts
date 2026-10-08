// Typed client for the /stats API (app/routers/stats.py)

export type CountBy = 'word' | 'stem' | 'lemma' | 'root'

export interface Summary {
  ayas: number
  words: number
  words_uthmani: number
  roots: number
  lemmas: number
}

export interface Surah {
  id: number
  name_arabic: string
  name_transliterated: string
  name_english: string
  revelation_type: 'meccan' | 'medinan'
  aya_count: number
}

export interface Frequency {
  value: string
  count: number
}

export interface Count {
  by: CountBy
  query: string
  count: number
  breakdown: Frequency[]
}

type Params = Record<string, string | number | string[]>

async function get<T>(path: string, params: Params, signal?: AbortSignal): Promise<T> {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    for (const item of Array.isArray(value) ? value : [value]) search.append(key, String(item))
  }
  const response = await fetch(`${path}?${search}`, { signal })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(errorMessage(body) ?? `Request failed (${response.status})`)
  return body as T
}

// FastAPI errors: {detail: "message"} from HTTPException, {detail: [{msg}]} from validation
function errorMessage(body: unknown): string | undefined {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join('; ')
}

export const getSummary = (range: string[], signal?: AbortSignal) =>
  get<Summary>('/stats/summary', { range }, signal)

export const getCount = (range: string[], by: CountBy, q: string, signal?: AbortSignal) =>
  get<Count>('/stats/count', { range, by, q }, signal)

export const getTop = (range: string[], by: CountBy, limit: number, signal?: AbortSignal) =>
  get<Frequency[]>('/stats/top', { range, by, limit }, signal)

export const getSurahs = (signal?: AbortSignal) => get<Surah[]>('/surahs', {}, signal)
