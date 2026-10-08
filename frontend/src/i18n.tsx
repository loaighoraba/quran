import { createContext, useContext, type ReactNode } from 'react'
import type { CountBy, Surah } from './api'
import { Ar } from './Ar'
import type { RangeProblem } from './ranges'

export type Locale = 'ar' | 'en'
export const LOCALES: Locale[] = ['ar', 'en']
export const DEFAULT_LOCALE: Locale = 'ar'

type Plural = Partial<Record<Intl.LDMLPluralRule, string>> & { other: string }

// Every language must define every key; TypeScript checks `ar` against this shape
interface Messages {
  title: string
  subtitle: string
  otherLanguage: string
  ayas: string
  wholeQuran: string
  presets: Record<'fatiha' | 'baqarah' | 'maryam' | 'amma', string>
  chooseSurah: string
  surahOption: (surah: Surah, number: string) => string
  ayasLabel: string
  to: string
  of: (count: string) => string
  removeSurah: string
  addSurah: string
  spansSurahs: (startOver: ReactNode) => ReactNode
  startOver: string
  orType: string
  rangePlaceholder: string
  apply: string
  rangeHint: (codes: Record<'surah' | 'surahs' | 'aya' | 'ayas' | 'across', ReactNode>) => ReactNode
  rangeProblem: (problem: RangeProblem, number: (n: number) => string) => string
  words: string
  wordsNote: ReactNode
  roots: string
  lemmas: string
  count: string
  countButton: string
  countInput: string
  by: Record<CountBy, { label: string; hint: ReactNode }>
  singleWord: string
  occurs: Plural // {n} is replaced by the formatted count
  mostFrequent: string
  top: (n: string) => string
  numberOfResults: string
  noResults: string
  countThis: string
  loading: string
  requestFailed: string
  footer: (links: Record<'tanzil' | 'cc' | 'corpus' | 'gpl' | 'fork', ReactNode>) => ReactNode
}

const en: Messages = {
  title: 'Quran Statistics',
  subtitle: 'Count words, stems, lemmas and roots across any ayas.',
  otherLanguage: 'العربية',
  ayas: 'Ayas',
  wholeQuran: 'Whole Quran',
  presets: { fatiha: 'Al-Fatiha', baqarah: 'Al-Baqarah 1–20', maryam: 'Maryam', amma: 'Juz ʿAmma' },
  chooseSurah: 'Choose a surah',
  surahOption: (s, n) => `${n}. ${s.name_transliterated} — ⁨${s.name_arabic}⁩`,
  ayasLabel: 'ayas',
  to: 'to',
  of: (count) => `of ${count}`,
  removeSurah: 'Remove this surah',
  addSurah: '+ Add surah',
  spansSurahs: (startOver) => (
    <>These ranges span several surahs, so edit them as text below, or {startOver}.</>
  ),
  startOver: 'start over by surah',
  orType: 'Or type ranges',
  rangePlaceholder: 'e.g. 2:1-20, 19, 3:5',
  apply: 'Apply',
  rangeHint: (c) => (
    <>
      Separate with commas: {c.surah} a surah, {c.surahs} surahs, {c.aya} an aya, {c.ayas} ayas,{' '}
      {c.across} across surahs. Empty means the whole Quran.
    </>
  ),
  rangeProblem: (p, n) => {
    switch (p.code) {
      case 'syntax':
        return `“${p.value}” isn't a range; use e.g. 2, 2-4, 2:255, 2:1-20 or 2:1-3:10`
      case 'noSurah':
        return `Surah ${n(p.surah)} doesn't exist; there are 114`
      case 'noAya':
        return `Surah ${n(p.surah)} has no aya ${n(p.aya)}`
      case 'backwards':
        return `“${p.value}” ends before it starts`
    }
  },
  words: 'Words',
  wordsNote: (
    <>
      with <Ar>يا</Ar> split off
    </>
  ),
  roots: 'Roots',
  lemmas: 'Lemmas',
  count: 'Count',
  countButton: 'Count',
  countInput: 'Text to count',
  by: {
    word: {
      label: 'Word',
      hint: (
        <>
          The written word: <Ar>مريم</Ar> matches <Ar>يا مريم</Ar>, not <Ar>ومريم</Ar>
        </>
      ),
    },
    stem: {
      label: 'Stem',
      hint: (
        <>
          Without prefixes and suffixes: <Ar>مريم</Ar> also matches <Ar>ومريم</Ar>
        </>
      ),
    },
    lemma: {
      label: 'Lemma',
      hint: (
        <>
          Every form of a word: <Ar>قال</Ar> matches <Ar>قالوا</Ar>, <Ar>يقول</Ar>, <Ar>قل</Ar>
        </>
      ),
    },
    root: {
      label: 'Root',
      hint: (
        <>
          Every word from the root: <Ar>رحم</Ar> matches <Ar>رحمن</Ar>, <Ar>رحيم</Ar>,{' '}
          <Ar>رحمة</Ar>
        </>
      ),
    },
  },
  singleWord: 'Enter a single word, without spaces',
  occurs: { one: 'occurs once', other: 'occurs {n} times' },
  mostFrequent: 'Most frequent',
  top: (n) => `Top ${n}`,
  numberOfResults: 'Number of results',
  noResults: 'No results in these ayas.',
  countThis: 'Count this',
  loading: 'Loading',
  requestFailed: "Couldn't load the data; try again.",
  footer: (l) => (
    <>
      Quran text from the {l.tanzil} ({l.cc}). Morphology, roots and lemmas from the {l.corpus} (
      {l.gpl}), via {l.fork}.
    </>
  ),
}

const ar: Messages = {
  title: 'إحصاءات القرآن',
  subtitle: 'عُدَّ الكلمات والجذوع والمداخل المعجمية والجذور في أي آيات.',
  otherLanguage: 'English',
  ayas: 'الآيات',
  wholeQuran: 'القرآن كاملًا',
  presets: { fatiha: 'الفاتحة', baqarah: 'البقرة ١–٢٠', maryam: 'مريم', amma: 'جزء عمّ' },
  chooseSurah: 'اختر سورة',
  surahOption: (s, n) => `${n}. ${s.name_arabic}`,
  ayasLabel: 'الآيات',
  to: 'إلى',
  of: (count) => `من ${count}`,
  removeSurah: 'احذف هذه السورة',
  addSurah: '+ أضف سورة',
  spansSurahs: (startOver) => (
    <>هذه النطاقات تمتد عبر عدة سور، فعدّلها نصًّا في الأسفل، أو {startOver}.</>
  ),
  startOver: 'ابدأ من جديد باختيار السور',
  orType: 'أو اكتب النطاقات',
  rangePlaceholder: 'مثلًا 2:1-20, 19, 3:5',
  apply: 'تطبيق',
  rangeHint: (c) => (
    <>
      افصل بينها بفواصل: {c.surah} سورة، {c.surahs} سور، {c.aya} آية، {c.ayas} آيات، {c.across}{' '}
      عبر السور. الحقل الفارغ يعني القرآن كاملًا.
    </>
  ),
  rangeProblem: (p, n) => {
    switch (p.code) {
      case 'syntax':
        return `«${p.value}» ليس نطاقًا صحيحًا؛ استخدم مثلًا 2 أو 2-4 أو 2:255 أو 2:1-20 أو 2:1-3:10`
      case 'noSurah':
        return `لا توجد سورة رقمها ${n(p.surah)}؛ عدد السور ${n(114)}`
      case 'noAya':
        return `لا توجد آية ${n(p.aya)} في السورة ${n(p.surah)}`
      case 'backwards':
        return `النطاق «${p.value}» ينتهي قبل أن يبدأ`
    }
  },
  words: 'الكلمات',
  wordsNote: (
    <>
      مع فصل <Ar>يا</Ar> النداء
    </>
  ),
  roots: 'الجذور',
  lemmas: 'المداخل المعجمية',
  count: 'العدّ',
  countButton: 'عُدّ',
  countInput: 'النص المراد عدّه',
  by: {
    word: {
      label: 'كلمة',
      hint: (
        <>
          الكلمة كما تُكتب: <Ar>مريم</Ar> تطابق <Ar>يا مريم</Ar> ولا تطابق <Ar>ومريم</Ar>
        </>
      ),
    },
    stem: {
      label: 'جذع',
      hint: (
        <>
          الكلمة بلا سوابق ولواحق: <Ar>مريم</Ar> تطابق <Ar>ومريم</Ar> أيضًا
        </>
      ),
    },
    lemma: {
      label: 'مدخل معجمي',
      hint: (
        <>
          كل صيغ الكلمة: <Ar>قال</Ar> تطابق <Ar>قالوا</Ar> و<Ar>يقول</Ar> و<Ar>قل</Ar>
        </>
      ),
    },
    root: {
      label: 'جذر',
      hint: (
        <>
          كل الكلمات من الجذر: <Ar>رحم</Ar> يطابق <Ar>رحمن</Ar> و<Ar>رحيم</Ar> و<Ar>رحمة</Ar>
        </>
      ),
    },
  },
  singleWord: 'أدخل كلمة واحدة بلا مسافات',
  occurs: {
    zero: 'لا ترد',
    one: 'ترد مرة واحدة',
    two: 'ترد مرتين',
    few: 'ترد {n} مرات',
    many: 'ترد {n} مرة',
    other: 'ترد {n} مرة',
  },
  mostFrequent: 'الأكثر تكرارًا',
  top: (n) => `أعلى ${n}`,
  numberOfResults: 'عدد النتائج',
  noResults: 'لا نتائج في هذه الآيات.',
  countThis: 'عُدّ هذا',
  loading: 'جارٍ التحميل',
  requestFailed: 'تعذّر تحميل البيانات؛ حاول مرة أخرى.',
  footer: (l) => (
    <>
      نص القرآن من {l.tanzil} ({l.cc}). الصرف والجذور والمداخل المعجمية من {l.corpus} ({l.gpl})،
      عبر {l.fork}.
    </>
  ),
}

const MESSAGES: Record<Locale, Messages> = { ar, en }
// Arabic-Indic digits in Arabic: ٧٧٬٧٩٠
const NUMBER_LOCALES: Record<Locale, string> = { ar: 'ar-u-nu-arab', en: 'en' }

export function makeI18n(locale: Locale) {
  const numbers = new Intl.NumberFormat(NUMBER_LOCALES[locale])
  const plurals = new Intl.PluralRules(locale)
  const number = (n: number) => numbers.format(n)
  return {
    locale,
    dir: locale === 'ar' ? 'rtl' : 'ltr',
    t: MESSAGES[locale],
    number,
    plural: (forms: Plural, n: number) =>
      (forms[plurals.select(n)] ?? forms.other).replace('{n}', number(n)),
  } as const
}

export type I18n = ReturnType<typeof makeI18n>

export const I18nContext = createContext<I18n>(makeI18n(DEFAULT_LOCALE))
export const useI18n = () => useContext(I18nContext)
