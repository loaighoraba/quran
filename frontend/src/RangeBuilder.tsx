import { useMemo, useState } from 'react'
import type { Surah } from './api'
import { useI18n } from './i18n'
import { rowToText, textToRows } from './ranges'

// A row as typed: aya fields stay strings so they can be empty or invalid while being edited
interface Draft {
  id: number
  surah: number | null
  from: string
  to: string
}

let nextId = 1

const toDrafts = (text: string, ayaCounts: Map<number, number>): Draft[] =>
  (textToRows(text, ayaCounts) ?? []).map((row) => ({
    id: nextId++,
    surah: row.surah,
    from: String(row.from),
    to: String(row.to),
  }))

function ayaError(draft: Draft, ayaCount: number): 'from' | 'to' | null {
  const from = Number(draft.from)
  const to = Number(draft.to)
  if (!Number.isInteger(from) || from < 1 || from > ayaCount) return 'from'
  if (!Number.isInteger(to) || to < 1 || to > ayaCount || to < from) return 'to'
  return null
}

/** Picks ranges as one row per surah; reads and writes the same text as the ranges input. */
export function RangeBuilder({
  value,
  surahs,
  onChange,
}: {
  value: string
  surahs: Surah[]
  onChange: (value: string) => void
}) {
  const { t, number } = useI18n()
  const ayaCounts = useMemo(() => new Map(surahs.map((s) => [s.id, s.aya_count])), [surahs])
  const [drafts, setDrafts] = useState(() => toDrafts(value, ayaCounts))
  // The text the rows were last synced with. When `value` changes from outside (the text input,
  // a preset, a link), rebuild the rows; when it's our own change echoing back, keep the drafts.
  const [synced, setSynced] = useState(value)
  if (value !== synced) {
    setSynced(value)
    setDrafts(toDrafts(value, ayaCounts))
  }

  const update = (next: Draft[]) => {
    setDrafts(next)
    // While an aya field is invalid, keep the last valid ranges rather than dropping the row
    // (which would jump to other ayas, or to the whole Quran) until the user fixes it
    if (next.some((d) => d.surah !== null && ayaError(d, ayaCounts.get(d.surah)!))) return
    // Rows without a surah yet are skipped
    const text = next
      .filter((d) => d.surah !== null)
      .map((d) => {
        const count = ayaCounts.get(d.surah!)!
        return rowToText({ surah: d.surah!, from: Number(d.from), to: Number(d.to) }, count)
      })
      .join(', ')
    setSynced(text)
    if (text !== value) onChange(text)
  }

  const change = (id: number, changes: Partial<Draft>) =>
    update(drafts.map((d) => (d.id === id ? { ...d, ...changes } : d)))

  if (value && textToRows(value, ayaCounts) === null) {
    return (
      <div className="builder">
        <p className="hint">
          {t.spansSurahs(
            <button type="button" className="link" onClick={() => onChange('')}>
              {t.startOver}
            </button>,
          )}
        </p>
      </div>
    )
  }

  return (
    <div className="builder">
      {drafts.map((draft) => {
        const count = draft.surah === null ? undefined : ayaCounts.get(draft.surah)
        const error = count === undefined ? null : ayaError(draft, count)
        return (
          <div className="builder-row" key={draft.id}>
            <select
              value={draft.surah ?? ''}
              onChange={(e) => {
                const surah = Number(e.target.value)
                // A new surah starts as all of it
                change(draft.id, { surah, from: '1', to: String(ayaCounts.get(surah)) })
              }}
              aria-label={t.chooseSurah}
            >
              <option value="" disabled>
                {t.chooseSurah}
              </option>
              {surahs.map((s) => (
                <option key={s.id} value={s.id}>
                  {t.surahOption(s, number(s.id))}
                </option>
              ))}
            </select>
            <span className="aya-range">
              <span className="muted">{t.ayasLabel}</span>
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={count}
                value={draft.from}
                disabled={count === undefined}
                aria-invalid={error === 'from'}
                aria-label="From aya"
                onChange={(e) => change(draft.id, { from: e.target.value })}
              />
              <span className="muted">{t.to}</span>
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={count}
                value={draft.to}
                disabled={count === undefined}
                aria-invalid={error === 'to'}
                aria-label="To aya"
                onChange={(e) => change(draft.id, { to: e.target.value })}
              />
              <span className="muted of">{count !== undefined && t.of(number(count))}</span>
            </span>
            <button
              type="button"
              className="remove"
              onClick={() => update(drafts.filter((d) => d.id !== draft.id))}
              aria-label={t.removeSurah}
              title={t.removeSurah}
            >
              ✕
            </button>
          </div>
        )
      })}
      <button
        type="button"
        className="add"
        onClick={() => setDrafts([...drafts, { id: nextId++, surah: null, from: '', to: '' }])}
      >
        {t.addSurah}
      </button>
    </div>
  )
}
