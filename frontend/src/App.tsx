import { useEffect, useEffectEvent, useState, type FormEvent, type ReactNode } from 'react'
import { getCount, getSummary, getTop, type CountBy, type Frequency } from './api'

// Arabic inside English text, isolated so its direction doesn't reorder the sentence
const Ar = ({ children }: { children: string }) => (
  <bdi lang="ar" className="arabic">
    {children}
  </bdi>
)

const BY_OPTIONS: { value: CountBy; label: string; hint: ReactNode }[] = [
  {
    value: 'word',
    label: 'Word',
    hint: (
      <>
        The written word: <Ar>مريم</Ar> matches <Ar>يا مريم</Ar>, not <Ar>ومريم</Ar>
      </>
    ),
  },
  {
    value: 'stem',
    label: 'Stem',
    hint: (
      <>
        Without prefixes and suffixes: <Ar>مريم</Ar> also matches <Ar>ومريم</Ar>
      </>
    ),
  },
  {
    value: 'lemma',
    label: 'Lemma',
    hint: (
      <>
        Every form of a word: <Ar>قال</Ar> matches <Ar>قالوا</Ar>, <Ar>يقول</Ar>, <Ar>قل</Ar>
      </>
    ),
  },
  {
    value: 'root',
    label: 'Root',
    hint: (
      <>
        Every word from the root: <Ar>رحم</Ar> matches <Ar>رحمن</Ar>, <Ar>رحيم</Ar>,{' '}
        <Ar>رحمة</Ar>
      </>
    ),
  },
]

const RANGE_EXAMPLES = [
  { label: 'Al-Fatiha', value: '1' },
  { label: 'Al-Baqarah 1–20', value: '2:1-20' },
  { label: 'Maryam', value: '19' },
  { label: 'Juz ʿAmma', value: '78-114' },
]

const TOP_LIMITS = [10, 20, 50, 100]

// "2:1-20, 19  3:5" -> ["2:1-20", "19", "3:5"]
const parseRanges = (text: string) => text.split(/[\s,،]+/).filter(Boolean)

// App state lives in the URL, so every view can be bookmarked and shared
function readUrl() {
  const params = new URLSearchParams(window.location.search)
  const by = (name: string, fallback: CountBy) => {
    const value = params.get(name)
    return BY_OPTIONS.some((o) => o.value === value) ? (value as CountBy) : fallback
  }
  return {
    ranges: params.get('range') ?? '',
    countBy: by('by', 'root'),
    q: params.get('q') ?? '',
    topBy: by('top', 'root'),
    limit: Number(params.get('limit')) || 20,
  }
}

type State = ReturnType<typeof readUrl>

function writeUrl(state: State) {
  const params = new URLSearchParams()
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

export default function App() {
  const [state, setState] = useState(readUrl)
  const [rangeInput, setRangeInput] = useState(state.ranges)
  const [qInput, setQInput] = useState(state.q)
  const update = (changes: Partial<State>) => setState((s) => ({ ...s, ...changes }))

  useEffect(() => writeUrl(state), [state])

  const ranges = parseRanges(state.ranges)
  const rangeKey = ranges.join(' ')

  const summary = useRequest(rangeKey, (signal) => getSummary(ranges, signal))
  const count = useRequest(state.q ? `${rangeKey}|${state.countBy}|${state.q}` : null, (signal) =>
    getCount(ranges, state.countBy, state.q, signal),
  )
  const top = useRequest(`${rangeKey}|${state.topBy}|${state.limit}`, (signal) =>
    getTop(ranges, state.topBy, state.limit, signal),
  )

  // An invalid range fails every request; show its error once, under the range input
  const rangeError = summary.error

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

  return (
    <main>
      <header>
        <h1>Quran Statistics</h1>
        <p className="subtitle">Count words, stems, lemmas and roots across any ayas.</p>
      </header>

      <section className="card">
        <form className="range-form" onSubmit={submitRanges}>
          <label htmlFor="range">Ayas</label>
          <div className="row">
            <input
              id="range"
              value={rangeInput}
              onChange={(e) => setRangeInput(e.target.value)}
              placeholder="The whole Quran — or e.g. 2:1-20, 19, 3:5"
              dir="ltr"
              autoComplete="off"
            />
            <button type="submit">Apply</button>
          </div>
        </form>
        <div className="chips">
          <button
            type="button"
            className={!state.ranges ? 'chip active' : 'chip'}
            onClick={() => applyRanges('')}
          >
            Whole Quran
          </button>
          {RANGE_EXAMPLES.map((example) => (
            <button
              key={example.value}
              type="button"
              className={state.ranges === example.value ? 'chip active' : 'chip'}
              onClick={() => applyRanges(example.value)}
            >
              {example.label}
            </button>
          ))}
        </div>
        <p className="hint">
          Separate ranges with commas: <code>2</code> a surah, <code>2-4</code> surahs,{' '}
          <code>2:255</code> an aya, <code>2:1-20</code> ayas, <code>2:1-3:10</code> across surahs.
        </p>

        {rangeError ? (
          <p className="error">{rangeError}</p>
        ) : (
          <dl className={summary.loading ? 'tiles loading' : 'tiles'}>
            <Tile label="Ayas" value={summary.data?.ayas} />
            <Tile label="Words" value={summary.data?.words} note={<>with <Ar>يا</Ar> split off</>} />
            <Tile label="Uthmani words" value={summary.data?.words_uthmani} />
            <Tile label="Roots" value={summary.data?.roots} />
            <Tile label="Lemmas" value={summary.data?.lemmas} />
          </dl>
        )}
      </section>

      <section className="card" id="count">
        <h2>Count</h2>
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
              aria-label="Text to count"
            />
            <button type="submit">Count</button>
          </div>
          <p className="hint">{BY_OPTIONS.find((o) => o.value === state.countBy)?.hint}</p>
        </form>
        {count.error && !rangeError && <p className="error">{count.error}</p>}
        {count.data && !count.error && (
          <div className={count.loading ? 'loading' : undefined}>
            <p className="total">
              <Ar>{count.data.query}</Ar>{' '}
              occurs <strong>{count.data.count.toLocaleString()}</strong>{' '}
              {count.data.count === 1 ? 'time' : 'times'}
            </p>
            {count.data.breakdown.length > 1 && <Bars items={count.data.breakdown} />}
          </div>
        )}
      </section>

      <section className="card">
        <div className="card-heading">
          <h2>Most frequent</h2>
          <select
            value={state.limit}
            onChange={(e) => update({ limit: Number(e.target.value) })}
            aria-label="Number of results"
          >
            {TOP_LIMITS.map((limit) => (
              <option key={limit} value={limit}>
                Top {limit}
              </option>
            ))}
          </select>
        </div>
        <ByPicker value={state.topBy} onChange={(topBy) => update({ topBy })} />
        {top.error && !rangeError && <p className="error">{top.error}</p>}
        {top.data && !top.error && (
          <div className={top.loading ? 'loading' : undefined}>
            <Bars items={top.data} onSelect={countValue} />
          </div>
        )}
      </section>

      {/* Both sources require being named, with a link, wherever their data is used */}
      <footer>
        <p>
          Quran text from the{' '}
          <a href="https://tanzil.net" target="_blank" rel="noreferrer">
            Tanzil Project
          </a>{' '}
          (
          <a
            href="https://creativecommons.org/licenses/by/3.0/"
            target="_blank"
            rel="noreferrer"
          >
            CC BY 3.0
          </a>
          ). Morphology, roots and lemmas from the{' '}
          <a href="https://corpus.quran.com" target="_blank" rel="noreferrer">
            Quranic Arabic Corpus
          </a>{' '}
          (
          <a href="https://corpus.quran.com/license.jsp" target="_blank" rel="noreferrer">
            GNU GPL
          </a>
          ), via{' '}
          <a href="https://github.com/mustafa0x/quran-morphology" target="_blank" rel="noreferrer">
            mustafa0x/quran-morphology
          </a>
          .
        </p>
      </footer>
    </main>
  )
}

function Tile({ label, value, note }: { label: string; value?: number; note?: ReactNode }) {
  return (
    <div className="tile">
      <dt>{label}</dt>
      <dd>{value === undefined ? '—' : value.toLocaleString()}</dd>
      {note && <span className="note">{note}</span>}
    </div>
  )
}

function ByPicker({ value, onChange }: { value: CountBy; onChange: (by: CountBy) => void }) {
  return (
    <div className="segmented" role="radiogroup" aria-label="Match by">
      {BY_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className={value === option.value ? 'active' : undefined}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

function Bars({ items, onSelect }: { items: Frequency[]; onSelect?: (value: string) => void }) {
  if (items.length === 0) return <p className="hint">No results in these ayas.</p>
  const max = Math.max(...items.map((item) => item.count))
  return (
    <ol className="bars">
      {items.map((item) => (
        <li key={item.value}>
          {onSelect ? (
            <button
              type="button"
              className="bar-label arabic"
              lang="ar"
              onClick={() => onSelect(item.value)}
              title="Count this"
            >
              {item.value}
            </button>
          ) : (
            <span className="bar-label arabic" lang="ar">
              {item.value}
            </span>
          )}
          <span className="bar-track">
            <span className="bar" style={{ width: `${(item.count / max) * 100}%` }} />
          </span>
          <span className="bar-count">{item.count.toLocaleString()}</span>
        </li>
      ))}
    </ol>
  )
}
