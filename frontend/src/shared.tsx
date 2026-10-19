import type { CountBy } from './api'
import { useI18n, type Locale } from './i18n'
import { BY_VALUES, useDelayed } from './lib'

export function Spinner({ active }: { active: boolean }) {
  const { t } = useI18n()
  const shown = useDelayed(active)
  return shown ? <span className="spinner" role="status" aria-label={t.loading} /> : null
}

export function ByPicker({ value, onChange }: { value: CountBy; onChange: (by: CountBy) => void }) {
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

// Title, language switch and subtitle, shared by every page
export function Header({
  title,
  subtitle,
  locale,
  onLocale,
  homeHref,
}: {
  title: string
  subtitle: string
  locale: Locale
  onLocale: (locale: Locale) => void
  homeHref: string
}) {
  const { t } = useI18n()
  return (
    <header>
      <div className="title-row">
        {/* A plain link: reloads the page, clearing every filter of the current page */}
        <h1>
          <a href={homeHref} className="home">
            {title}
          </a>
        </h1>
        <button
          type="button"
          className="language"
          lang={locale === 'ar' ? 'en' : 'ar'}
          onClick={() => onLocale(locale === 'ar' ? 'en' : 'ar')}
        >
          {t.otherLanguage}
        </button>
      </div>
      <p className="subtitle">{subtitle}</p>
    </header>
  )
}
