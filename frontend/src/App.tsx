import { useEffect, useEffectEvent, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { getCount, getSummary, getSurahs, getTop, type CountBy, type Frequency } from './api'
import { Ar } from './Ar'
import {
  DEFAULT_LOCALE,
  I18nContext,
  LOCALES,
  makeI18n,
  useI18n,
  type Locale,
} from './i18n'
import { RangeBuilder } from './RangeBuilder'
import { findRangeProblem, splitRanges } from './ranges'

const BY_VALUES: CountBy[] = ['word', 'stem', 'lemma', 'root']

const PRESETS = [
  { key: 'fatiha', value: '1' },
  { key: 'baqarah', value: '2:1-20' },
  { key: 'maryam', value: '19' },
  { key: 'amma', value: '78-114' },
] as const

const TOP_LIMITS = [10, 20, 50, 100]

const LOCALE_STORAGE_KEY = 'locale'

// Storage can be unavailable (private windows, blocked site data); the language is a convenience
function storedLocale(): string | null {
  try {
    return localStorage.getItem(LOCALE_STORAGE_KEY)
  } catch {
    return null
  }
}

function storeLocale(locale: Locale) {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    // Not remembered; the URL still carries it
  }
}

const asLocale = (value: string | null) => LOCALES.find((l) => l === value)

// App state lives in the URL, so every view can be bookmarked and shared
function readUrl() {
  const params = new URLSearchParams(window.location.search)
  const by = (name: string) => BY_VALUES.find((v) => v === params.get(name)) ?? 'word'
  return {
    locale: asLocale(params.get('lang')) ?? asLocale(storedLocale()) ?? DEFAULT_LOCALE,
    ranges: params.get('range') ?? '',
    countBy: by('by'),
    q: params.get('q') ?? '',
    topBy: by('top'),
    limit: Number(params.get('limit')) || 20,
  }
}

type State = ReturnType<typeof readUrl>

function writeUrl(state: State) {
  const params = new URLSearchParams()
  params.set('lang', state.locale)
  if (state.ranges) params.set('range', state.ranges)
  if (state.q) params.set('q', state.q)
  params.set('by', state.countBy)
  params.set('top', state.topBy)
  params.set('limit', String(state.limit))
  window.history.replaceState(null, '', `?${params}`)
}

// Runs the request whenever `key` changes (null: no request), cancelling the previous one.
// `key` must capture every input the request uses. Data from the previous key stays visible
// while the next one loads.
function useRequest<T>(key: string | null, request: (signal: AbortSignal) => Promise<T>) {
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
function useDelayed(active: boolean, delay = 200) {
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

function Spinner({ active }: { active: boolean }) {
  const { t } = useI18n()
  const shown = useDelayed(active)
  return shown ? <span className="spinner" role="status" aria-label={t.loading} /> : null
}

export default function App() {
  const [state, setState] = useState(readUrl)
  const [rangeInput, setRangeInput] = useState(state.ranges)
  const [qInput, setQInput] = useState(state.q)
  const update = (changes: Partial<State>) => setState((s) => ({ ...s, ...changes }))

  const i18n = useMemo(() => makeI18n(state.locale), [state.locale])
  const { t, number, plural } = i18n

  useEffect(() => writeUrl(state), [state])

  useEffect(() => {
    document.documentElement.lang = i18n.locale
    document.documentElement.dir = i18n.dir
    document.title = i18n.t.title
  }, [i18n])

  const setLocale = (locale: Locale) => {
    storeLocale(locale)
    update({ locale })
  }

  const ranges = splitRanges(state.ranges)
  const rangeKey = ranges.join(' ')

  const surahs = useRequest('surahs', (signal) => getSurahs(signal))
  const ayaCounts = useMemo(
    () => new Map((surahs.data ?? []).map((s) => [s.id, s.aya_count])),
    [surahs.data],
  )
  // Checked here, once the surahs are known, so the message is in the UI language and no
  // request is sent for ranges the API would reject
  const rangeProblem = surahs.data ? findRangeProblem(state.ranges, ayaCounts) : null
  const qProblem = state.countBy !== 'root' && /\s/.test(state.q)

  const summary = useRequest(rangeProblem ? null : rangeKey, (signal) =>
    getSummary(ranges, signal),
  )
  const count = useRequest(
    state.q && !rangeProblem && !qProblem ? `${rangeKey}|${state.countBy}|${state.q}` : null,
    (signal) => getCount(ranges, state.countBy, state.q, signal),
  )
  const top = useRequest(rangeProblem ? null : `${rangeKey}|${state.topBy}|${state.limit}`, (signal) =>
    getTop(ranges, state.topBy, state.limit, signal),
  )

  // An invalid range would fail every request; show its message once, in the ayas card
  const rangeError = rangeProblem ? t.rangeProblem(rangeProblem, number) : summary.error && t.requestFailed

  const applyRanges = (value: string) => {
    setRangeInput(value)
    update({ ranges: value.trim() })
  }

  const submitRanges = (event: FormEvent) => {
    event.preventDefault()
    applyRanges(rangeInput)
  }

  const submitCount = (event: FormEvent) => {
    event.preventDefault()
    update({ q: qInput.trim() })
  }

  // Clicking a frequent value counts it, with the same matching
  const countValue = (value: string) => {
    setQInput(value)
    update({ q: value, countBy: state.topBy })
    document.getElementById('count')?.scrollIntoView({ behavior: 'smooth' })
  }

  const code = (text: string) => <code dir="ltr">{text}</code>
  const link = (href: string, text: string) => (
    <a href={href} target="_blank" rel="noreferrer">
      {text}
    </a>
  )

  return (
    <I18nContext value={i18n}>
      <main>
        <header>
          <div className="title-row">
            {/* A plain link: reloads the page with no query string, clearing every filter */}
            <h1>
              <a href={`/?lang=${state.locale}`} className="home">
                {t.title}
              </a>
            </h1>
            <button
              type="button"
              className="language"
              lang={state.locale === 'ar' ? 'en' : 'ar'}
              onClick={() => setLocale(state.locale === 'ar' ? 'en' : 'ar')}
            >
              {t.otherLanguage}
            </button>
          </div>
          <p className="subtitle">{t.subtitle}</p>
        </header>

        <section className="card">
          <div className="card-heading">
            <h2>
              {t.ayas} <Spinner active={summary.loading} />
            </h2>
          </div>
          <div className="chips">
            <button
              type="button"
              className={!state.ranges ? 'chip active' : 'chip'}
              onClick={() => applyRanges('')}
            >
              {t.wholeQuran}
            </button>
            {PRESETS.map((preset) => (
              <button
                key={preset.key}
                type="button"
                className={state.ranges === preset.value ? 'chip active' : 'chip'}
                onClick={() => applyRanges(preset.value)}
              >
                {t.presets[preset.key]}
              </button>
            ))}
          </div>

          {surahs.data && (
            <RangeBuilder value={state.ranges} surahs={surahs.data} onChange={applyRanges} />
          )}

          <form className="range-form" onSubmit={submitRanges}>
            <label htmlFor="range">{t.orType}</label>
            <div className="row compact">
              <input
                id="range"
                value={rangeInput}
                onChange={(e) => setRangeInput(e.target.value)}
                placeholder={t.rangePlaceholder}
                dir="ltr"
                autoComplete="off"
              />
              <button type="submit">{t.apply}</button>
            </div>
            <p className="hint">
              {t.rangeHint({
                surah: code('2'),
                surahs: code('2-4'),
                aya: code('2:255'),
                ayas: code('2:1-20'),
                across: code('2:1-3:10'),
              })}
            </p>
          </form>

          {rangeError ? (
            <p className="error">{rangeError}</p>
          ) : (
            <dl className={summary.loading ? 'tiles loading' : 'tiles'}>
              <Tile label={t.ayas} value={summary.data?.ayas} loading={summary.loading} />
              <Tile
                label={t.words}
                value={summary.data?.words}
                loading={summary.loading}
                note={t.wordsNote}
              />
              <Tile label={t.roots} value={summary.data?.roots} loading={summary.loading} />
              <Tile label={t.lemmas} value={summary.data?.lemmas} loading={summary.loading} />
            </dl>
          )}
        </section>

        <section className="card" id="count">
          <div className="card-heading">
            <h2>
              {t.count} <Spinner active={count.loading} />
            </h2>
          </div>
          <form className="count-form" onSubmit={submitCount}>
            <ByPicker value={state.countBy} onChange={(countBy) => update({ countBy })} />
            <div className="row">
              <input
                value={qInput}
                onChange={(e) => setQInput(e.target.value)}
                placeholder="مريم"
                dir="rtl"
                lang="ar"
                className="arabic"
                autoComplete="off"
                aria-label={t.countInput}
              />
              <button type="submit">{t.countButton}</button>
            </div>
            <p className="hint">{t.by[state.countBy].hint}</p>
          </form>
          {qProblem && !rangeError && <p className="error">{t.singleWord}</p>}
          {count.error && !rangeError && <p className="error">{t.requestFailed}</p>}
          {!count.data && count.loading && <SkeletonBars rows={3} />}
          {count.data && !count.error && !qProblem && (
            <div className={count.loading ? 'loading' : undefined}>
              <p className="total">
                <Ar>{count.data.query}</Ar> <strong>{plural(t.occurs, count.data.count)}</strong>
              </p>
              {count.data.breakdown.length > 1 && <Bars items={count.data.breakdown} />}
            </div>
          )}
        </section>

        <section className="card">
          <div className="card-heading">
            <h2>
              {t.mostFrequent} <Spinner active={top.loading} />
            </h2>
            <select
              value={state.limit}
              onChange={(e) => update({ limit: Number(e.target.value) })}
              aria-label={t.numberOfResults}
            >
              {TOP_LIMITS.map((limit) => (
                <option key={limit} value={limit}>
                  {t.top(number(limit))}
                </option>
              ))}
            </select>
          </div>
          <ByPicker value={state.topBy} onChange={(topBy) => update({ topBy })} />
          {top.error && !rangeError && <p className="error">{t.requestFailed}</p>}
          {!top.data && top.loading && <SkeletonBars rows={8} />}
          {top.data && !top.error && (
            <div className={top.loading ? 'loading' : undefined}>
              <Bars items={top.data} onSelect={countValue} />
            </div>
          )}
        </section>

        {/* Both sources require being named, with a link, wherever their data is used */}
        <footer>
          <p>
            {t.footer({
              tanzil: link('https://tanzil.net', 'Tanzil Project'),
              cc: link('https://creativecommons.org/licenses/by/3.0/', 'CC BY 3.0'),
              corpus: link('https://corpus.quran.com', 'Quranic Arabic Corpus'),
              gpl: link('https://corpus.quran.com/license.jsp', 'GNU GPL'),
              fork: link('https://github.com/mustafa0x/quran-morphology', 'mustafa0x/quran-morphology'),
            })}
          </p>
        </footer>
      </main>
    </I18nContext>
  )
}

function Tile({
  label,
  value,
  note,
  loading,
}: {
  label: string
  value?: number
  note?: ReactNode
  loading: boolean
}) {
  const { number } = useI18n()
  let shown: ReactNode = '—'
  if (value !== undefined) shown = number(value)
  else if (loading) shown = <span className="skeleton skeleton-number" />
  return (
    <div className="tile">
      <dt>{label}</dt>
      <dd>{shown}</dd>
      {note && <span className="note">{note}</span>}
    </div>
  )
}

function ByPicker({ value, onChange }: { value: CountBy; onChange: (by: CountBy) => void }) {
  const { t } = useI18n()
  return (
    <div className="segmented" role="radiogroup">
      {BY_VALUES.map((by) => (
        <button
          key={by}
          type="button"
          role="radio"
          aria-checked={value === by}
          className={value === by ? 'active' : undefined}
          onClick={() => onChange(by)}
        >
          {t.by[by].label}
        </button>
      ))}
    </div>
  )
}

function Bars({ items, onSelect }: { items: Frequency[]; onSelect?: (value: string) => void }) {
  const { t, number } = useI18n()
  if (items.length === 0) return <p className="hint">{t.noResults}</p>
  const max = Math.max(...items.map((item) => item.count))
  return (
    <ol className="bars">
      {items.map((item) => (
        <li key={item.value}>
          {onSelect ? (
            <button
              type="button"
              className="bar-label arabic"
              onClick={() => onSelect(item.value)}
              title={t.countThis}
            >
              <bdi lang="ar">{item.value}</bdi>
            </button>
          ) : (
            <span className="bar-label arabic">
              <bdi lang="ar">{item.value}</bdi>
            </span>
          )}
          <span className="bar-track">
            <span className="bar" style={{ width: `${(item.count / max) * 100}%` }} />
          </span>
          <span className="bar-count">{number(item.count)}</span>
        </li>
      ))}
    </ol>
  )
}

// Placeholder rows shown before the first results arrive
function SkeletonBars({ rows }: { rows: number }) {
  return (
    <ol className="bars" aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <li key={index}>
          <span className="skeleton skeleton-label" />
          <span className="skeleton skeleton-bar" style={{ width: `${90 - index * 9}%` }} />
          <span className="skeleton skeleton-count" />
        </li>
      ))}
    </ol>
  )
}
