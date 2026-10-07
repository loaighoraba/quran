# quran

A web application that allows donig statistics on Quran.

## Development

```sh
cp .env.example .env  # then fill in your PostgreSQL credentials
uv sync
uv run alembic upgrade head  # apply database migrations
uv run python -m app.scripts.load_quran  # load the Quran text (safe to re-run)
uv run fastapi dev        # http://127.0.0.1:8000, docs at /docs
uv run pytest
```

## Quran data

`datasources/` holds the Quran text and surah metadata from the
[Tanzil Project](https://tanzil.net), licensed under
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). The files are kept
verbatim, as the license requires.

- `quran-simple.txt` / `quran-uthmani.txt`: `surah|aya|text` lines
- `quran-data.xml`: surah names, revelation type and order, aya counts

- `quran-morphology.txt`: word-by-word morphology from
  [mustafa0x/quran-morphology](https://github.com/mustafa0x/quran-morphology),
  a fork of the [Quranic Arabic Corpus](https://corpus.quran.com) v0.4 (GNU GPL).
  Each line is `surah:aya:word:segment`, the segment form, part of speech
  (`N`/`V`/`P`) and `|`-separated features. The fork's `morphology-terms.json`
  explains each tag.

The loader stores both scripts on each aya (`text_simple`, `text_uthmani`).
The basmala that Tanzil prepends to aya 1 of each surah (except 1 and 9) is
stripped from the aya text and recorded as `surahs.has_basmala` instead.

Morphology is in Uthmani script and goes into two tables:

- `words`: one row per word (77,429), with `text_uthmani` (the word's segments
  joined) and `text_normalized` (diacritics stripped, for loose search).
- `segments`: one row per morpheme (130,030), with `pos`, `kind`
  (prefix/stem/suffix), `root`, `lemma`, `verb_form`, `mood`, `family`, and the
  remaining tags in a `features` array.

There is no per-word simple text: the simple script splits some words
differently (`يَا أَيُّهَا` vs `يَٰٓأَيُّهَا`). To find a word whatever its
spelling, search by lemma. For phrase search in simple script, use
`ayas.text_simple`.

```sql
-- genitive nouns per root
SELECT root, count(*) FROM segments
WHERE pos = 'N' AND features @> '{GEN}' GROUP BY root ORDER BY 2 DESC;
```

## Database migrations

Models live in `app/models/` and must be imported in `app/models/__init__.py`
so Alembic can see them. After changing a model:

```sh
uv run alembic revision --autogenerate -m "describe the change"
# review the generated file in migrations/versions/, then:
uv run alembic upgrade head
```

### Supabase Data API

Tables are kept out of Supabase's Data API (REST): migration `3f8eb9f392f5`
enables row-level security (RLS) with no policies on every table and revokes the
API roles' grants. The app connects as the table owner, so RLS doesn't affect it.
Autogenerate doesn't add RLS, so **every migration that creates a table must also
run** `op.execute("ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY")`.

## Claude Code skills

`.claude/skills/` holds agent skills for Claude Code. `fastapi` is a symlink into
the FastAPI package inside `.venv`, so run `uv sync` first or it will be a broken link.
