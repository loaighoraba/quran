import { useEffect, useEffectEvent, useState } from 'react'
import type { CountBy } from './api'
import { LOCALES, type Locale } from './i18n'

export const BY_VALUES: CountBy[] = ['word', 'stem', 'lemma', 'root']

const LOCALE_STORAGE_KEY = 'locale'

// Storage can be unavailable (private windows, blocked site data); the language is a convenience
export function storedLocale(): string | null {
  try {
    return localStorage.getItem(LOCALE_STORAGE_KEY)
  } catch {
    return null
  }
}

export function storeLocale(locale: Locale) {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    // Not remembered; the URL still carries it
  }
}

export const asLocale = (value: string | null) => LOCALES.find((l) => l === value)

// Runs the request whenever `key` changes (null: no request), cancelling the previous one.
// `key` must capture every input the request uses. Data from the previous key stays visible
// while the next one loads.
export function useRequest<T>(key: string | null, request: (signal: AbortSignal) => Promise<T>) {
  const [result, setResult] = useState<{ key: string; data?: T; error?: string }>()
  const run = useEffectEvent(request)

  useEffect(() => {
    if (key === null) return
    const controller = new AbortController()
    run(controller.signal)
      .then((data) => setResult({ key, data }))
      .catch((error: Error) => {
        if (!controller.signal.aborted) setResult({ key, error: error.message })
      })
    return () => controller.abort()
  }, [key])

  if (key === null) return { loading: false }
  const current = result?.key === key
  return {
    data: result?.data,
    error: current ? result.error : undefined,
    loading: !current,
  }
}

// True once `active` has stayed true for `delay` ms, so fast requests don't flash a spinner
export function useDelayed(active: boolean, delay = 200) {
  const [elapsed, setElapsed] = useState(false)
  useEffect(() => {
    if (!active) return
    const timer = setTimeout(() => setElapsed(true), delay)
    return () => {
      clearTimeout(timer)
      setElapsed(false)
    }
  }, [active, delay])
  return active && elapsed
}
