import { Fragment, useEffect, useMemo, useState, type FormEvent } from 'react'
import { getAyas, getSurahs } from './api'
import { Ar } from './Ar'
import { DEFAULT_LOCALE, I18nContext, makeI18n, useI18n, type Locale } from './i18n'
import { splitRanges } from './ranges'
import { asLocale, BY_VALUES, storedLocale, storeLocale, useRequest } from './lib'
import { ByPicker, Header, Spinner } from './shared'

const PAGE_SIZE = 10

// Like the main page, state lives in the URL; this page lives at /ayas
function readUrl() {
  const params = new URLSearchParams(window.location.search)
  return {
    locale: asLocale(params.get('lang')) ?? asLocale(storedLocale()) ?? DEFAULT_LOCALE,
    ranges: params.get('range') ?? '',
    by: BY_VALUES.find((v) => v === params.get('by')) ?? 'word',
    q: params.get('q') ?? '',
    page: Math.max(1, Number(params.get('page')) || 1),
  }
}

type State = ReturnType<typeof readUrl>

function writeUrl(state: State) {
  const params = new URLSearchParams({ lang: state.locale })
  if (state.ranges) params.set('range', state.ranges)
  params.set('by', state.by)
  if (state.q) params.set('q', state.q)
  if (state.page > 1) params.set('page', String(state.page))
  window.history.replaceState(null, '', `/ayas?${params}`)
}

export default function AyasPage() {
  const [state, setState] = useState(readUrl)
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
  const qProblem = state.by !== 'root' && /\s/.test(state.q)
  const surahs = useRequest('surahs', (signal) => getSurahs(signal))
  const result = useRequest(
    state.q && !qProblem
      ? `${ranges.join(' ')}|${state.by}|${state.q}|${state.page}`
      : null,
    (signal) => getAyas(ranges, state.by, state.q, state.page, PAGE_SIZE, signal),
  )

  const surahName = (id: number) => {
    const surah = surahs.data?.find((s) => s.id === id)
    if (!surah) return number(id)
    return state.locale === 'ar' ? surah.name_arabic : surah.name_transliterated
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    update({ q: qInput.trim(), page: 1 })
  }

  const goTo = (page: number) => {
    update({ page })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const back = new URLSearchParams({ lang: state.locale, by: state.by })
  if (state.ranges) back.set('range', state.ranges)
  if (state.q) back.set('q', state.q)

  const pages = result.data ? Math.max(1, Math.ceil(result.data.total / PAGE_SIZE)) : 1

  return (
    <I18nContext value={i18n}>
      <main>
        <Header
          title={t.title}
          subtitle={t.ayasPageSubtitle}
          locale={state.locale}
          onLocale={setLocale}
          homeHref={`/?lang=${state.locale}`}
        />

        <section className="card">
          <div className="card-heading">
            <h2>
              {t.ayas} <Spinner active={result.loading} />
            </h2>
            <a href={`/?${back}`}>{t.backToStats}</a>
          </div>
          <form className="count-form" onSubmit={submit}>
            <ByPicker value={state.by} onChange={(by) => update({ by, page: 1 })} />
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
            <p className="hint">{t.by[state.by].hint}</p>
          </form>
          <p className="hint">
            {t.searchIn(state.ranges ? <code dir="ltr">{state.ranges}</code> : t.wholeQuran)}
          </p>
          {qProblem && <p className="error">{t.singleWord}</p>}
          {result.error && <p className="error">{t.requestFailed}</p>}
        </section>

        {result.data && !result.error && !qProblem && (
          <div className={result.loading ? 'loading' : undefined}>
            <p className="total">
              <Ar>{result.data.query}</Ar>: <strong>{plural(t.matchingAyas, result.data.total)}</strong>
            </p>
            {result.data.total === 0 && <p className="hint">{t.noResults}</p>}
            <ol className="aya-list">
              {result.data.ayas.map((aya) => (
                <li key={aya.id} className="card aya">
                  <p className="aya-ref">{t.surahAya(surahName(aya.surah), number(aya.number))}</p>
                  <p className="aya-text arabic" lang="ar" dir="rtl">
                    {aya.words.map((word, index) => (
                      <Fragment key={index}>
                        {word.matched ? <mark>{word.text}</mark> : word.text}{' '}
                      </Fragment>
                    ))}
                    <span className="aya-end">﴿{number(aya.number)}﴾</span>
                  </p>
                </li>
              ))}
            </ol>
            {pages > 1 && (
              <Pagination page={state.page} pages={pages} onPage={goTo} />
            )}
          </div>
        )}
      </main>
    </I18nContext>
  )
}

function Pagination({
  page,
  pages,
  onPage,
}: {
  page: number
  pages: number
  onPage: (page: number) => void
}) {
  const { t, number } = useI18n()
  return (
    <nav className="pagination" aria-label={t.pagination}>
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        {t.previous}
      </button>
      <span>{t.pageOf(number(page), number(pages))}</span>
      <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        {t.next}
      </button>
    </nav>
  )
}
