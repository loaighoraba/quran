// Converts between the range text the API takes ("2, 19:1-20") and one row per surah.
// Mirrors the syntax of app/ranges.py.

export interface RangeRow {
  surah: number
  from: number
  to: number
}

const RANGE = /^(\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$/

// "2:1-20, 19  3:5" -> ["2:1-20", "19", "3:5"]
export const splitRanges = (text: string) => text.split(/[\s,،]+/).filter(Boolean)

/** One row per range, or null when some range doesn't fit a single surah (2-4, 2:1-3:10). */
export function textToRows(text: string, ayaCounts: Map<number, number>): RangeRow[] | null {
  const rows: RangeRow[] = []
  for (const value of splitRanges(text)) {
    const match = RANGE.exec(value)
    if (!match) return null
    const [surah, startAya, endFirst, endAya] = match.slice(1).map((g) => (g ? Number(g) : null))
    const count = ayaCounts.get(surah!)
    if (count === undefined) return null
    let from = startAya ?? 1
    let to: number
    if (endFirst === null) {
      to = startAya ?? count
    } else if (endAya !== null) {
      if (endFirst !== surah) return null // 2:1-3:10 crosses surahs
      to = endAya
    } else if (startAya !== null) {
      to = endFirst // 2:1-20
    } else {
      if (endFirst !== surah) return null // 2-4: several surahs
      from = 1
      to = count
    }
    if (from < 1 || to > count || from > to) return null
    rows.push({ surah: surah!, from, to })
  }
  return rows
}

export function rowToText({ surah, from, to }: RangeRow, ayaCount: number): string {
  if (from === 1 && to === ayaCount) return String(surah)
  if (from === to) return `${surah}:${from}`
  return `${surah}:${from}-${to}`
}

export type RangeProblem =
  | { code: 'syntax'; value: string }
  | { code: 'noSurah'; surah: number }
  | { code: 'noAya'; surah: number; aya: number }
  | { code: 'backwards'; value: string }

/** The first problem in the ranges text, checked here so it can be shown in the UI language. */
export function findRangeProblem(text: string, ayaCounts: Map<number, number>): RangeProblem | null {
  for (const value of splitRanges(text)) {
    const match = RANGE.exec(value)
    if (!match) return { code: 'syntax', value }
    const [surah, startAya, endFirst, endAya] = match.slice(1).map((g) => (g ? Number(g) : null))
    // Same reading as app/ranges.py: 2:1-20 is ayas of surah 2, 2-4 is surahs
    const start = { surah: surah!, aya: startAya }
    let end: { surah: number; aya: number | null }
    if (endFirst === null) end = start
    else if (endAya !== null) end = { surah: endFirst, aya: endAya }
    else if (startAya !== null) end = { surah: surah!, aya: endFirst }
    else end = { surah: endFirst, aya: null }

    const ids: number[] = []
    for (const [ref, atEnd] of [
      [start, false],
      [end, true],
    ] as const) {
      const count = ayaCounts.get(ref.surah)
      if (count === undefined) return { code: 'noSurah', surah: ref.surah }
      const aya = ref.aya ?? (atEnd ? count : 1)
      if (aya < 1 || aya > count) return { code: 'noAya', surah: ref.surah, aya }
      ids.push(ref.surah * 1000 + aya) // orders positions without global aya ids
    }
    if (ids[0] > ids[1]) return { code: 'backwards', value }
  }
  return null
}
