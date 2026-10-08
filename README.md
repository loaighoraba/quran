# quran

A web application that allows doing statistics on Quran.

## Development

```sh
cp .env.example .env  # then fill in your PostgreSQL credentials
uv sync
uv run alembic upgrade head  # apply database migrations
uv run python -m app.scripts.load_quran  # load the Quran text (safe to re-run)
uv run fastapi dev        # http://127.0.0.1:8000, docs at /docs
uv run pytest
uv run python -m app.scripts.console  # IPython shell with the DB session and models loaded
```

### Frontend

`frontend/` is a React + TypeScript single-page app built with Vite. In
production FastAPI serves its build (`frontend/dist`) at `/`, next to the API,
so there is one origin and no CORS. Its state (ranges, query, options) lives in
the URL query string, so every view can be shared as a link.

```sh
cd frontend
npm install
npm run dev    # http://localhost:5173, proxies /stats to the API on :8000 (run fastapi dev too)
npm run lint
npm run build  # writes frontend/dist; then fastapi dev serves the app at :8000 as well
```

The interface is in Arabic (the default, right-to-left, Arabic-Indic digits) and
English. All text lives in `frontend/src/i18n.tsx`, one dictionary per language;
TypeScript fails the build if a language misses a key. The language is in the URL
(`?lang=en`), and the header toggle also remembers it in the browser.

Without a build, `fastapi dev` still starts (with a warning) but only the API works.
The Docker image builds the frontend in its own stage.

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
  joined), `text_normalized` (diacritics stripped, for loose search) and
  `split_normalized` (see below).
- `segments`: one row per morpheme (130,030), with `pos`, `kind`
  (prefix/stem/suffix), `form_normalized`, `root`, `lemma`, `verb_form`, `mood`,
  `family`, and the remaining tags in a `features` array.

The simple script writes the vocative يا as its own word (`يَا مَرْيَمُ`), where
the Uthmani script attaches it (`يَٰمَرْيَمُ`). `words.split_normalized` holds
the word split that way (`{يا,مريم}`; one element for every other word), and
word counts use it: 77,790 words. The vocative م of `اللهمّ` is a suffix and isn't
split. For phrase search in simple script, use `ayas.text_simple`.

```sql
-- genitive nouns per root
SELECT root, count(*) FROM segments
WHERE pos = 'N' AND features @> '{GEN}' GROUP BY root ORDER BY 2 DESC;
```

## Statistics API

All endpoints take optional, repeatable `range` parameters (omit for the whole
Quran): `2` (a surah), `2-4` (surahs), `2:255` (an aya), `2:1-20` (ayas of one
surah) or `2:1-3:10` (across surahs). Overlapping ranges are counted once.

- `GET /stats/summary`: aya, word, root and lemma counts. `words` counts the
  vocative يا as its own word; `words_uthmani` counts Uthmani words.
- `GET /stats/count?by=...&q=...`: occurrences of `q`, with a breakdown.
- `GET /stats/top?by=...&limit=20`: the most frequent values.
- `GET /surahs`: the 114 surahs with their names and aya counts, for picking
  ranges by name.

`by` sets what is matched, from strictest to loosest. Diacritics in `q` are
ignored, except that a fully diacritized lemma matches only itself.

| `by` | Matches | `q=مريم` / `q=قال` | Breakdown |
|---|---|---|---|
| `word` | The written word, vocative split off | مريم, يا مريم; not ومريم | Uthmani spellings |
| `stem` | The word without prefixes and suffixes | also ومريم | diacritized stems |
| `lemma` | Every form of a dictionary word | قال, قالوا, يقول, قل | matching lemmas |
| `root` | Every word from the root (`رحم` or `ر ح م`) | | the root's lemmas |

```sh
curl "localhost:8000/stats/count?by=root&q=رحم&range=1&range=2:1-20"
```

## Tests

`uv run pytest` runs the unit tests; the stats API tests are skipped. Those load
the full Quran into a database, replacing its data, so they only run with
`QURAN_TEST_DB=1` and refuse any host but localhost. Give them their own local
database, set up once:

```sh
createdb quran_test
cp .env .env.test  # then set POSTGRES_DB=quran_test and add QURAN_TEST_DB=1
uv run --env-file .env.test alembic upgrade head
```

Then run every test with:

```sh
uv run --env-file .env.test pytest
```

Run `uv run --env-file .env.test alembic upgrade head` again after adding a migration.

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

## Deployment

The API runs on DigitalOcean App Platform (app `quran`, region `fra`) as a
Docker container, served at https://quran.loaighoraba.dev (CNAME on Cloudflare, DNS only). The database is Supabase.

On every push to `main`, after the `test` job passes, the `deploy` job in
`.github/workflows/ci.yml` applies [.do/app.yaml](.do/app.yaml). App Platform
then builds the `Dockerfile`, runs `alembic upgrade head` as a pre-deploy job (a
failed migration stops the deploy), and rolls out the new version. `/health` is
the health check.

The data loader is not part of deployment. Run it from your machine against
Supabase when the source data changes.

`.env` points at your local database. Keep the Supabase credentials in
`.env.production` (git-ignored, like every `.env*` except `.env.example`) and
pass it explicitly; its values override `.env`:

```sh
uv run --env-file .env.production python -m app.scripts.load_quran
uv run --env-file .env.production python -m app.scripts.console
```

Required GitHub settings (Settings → Secrets and variables → Actions):

| Name | Kind | Value |
|---|---|---|
| `DIGITALOCEAN_ACCESS_TOKEN` | secret | DigitalOcean API token with App Platform read/write access |
| `POSTGRES_HOST` | secret | Supabase session pooler host |
| `POSTGRES_USER` | secret | `postgres.<project-ref>` |
| `POSTGRES_PASSWORD` | secret | Supabase database password |
| `APP_DOMAIN` | variable | Custom domain the app is served at, e.g. `quran.loaighoraba.dev` |
| `DO_PROJECT_ID` | variable | DigitalOcean project to create the app in (used on first deploy only) |

Build and run the image locally:

```sh
docker build -t quran .
docker run --rm --env-file .env -p 8080:8080 quran
```

## Claude Code skills

`.claude/skills/` holds agent skills for Claude Code. `fastapi` is a symlink into
the FastAPI package inside `.venv`, so run `uv sync` first or it will be a broken link.
