"""renormalize without small waw and yeh

Revision ID: 7f72e4368479
Revises: fd6e48a7d821
Create Date: 2026-10-08 09:59:04.321541

"""

import json
from collections.abc import Sequence
from itertools import groupby

import sqlalchemy as sa
from alembic import op

from app.arabic import normalize_arabic
from app.scripts.morphology import split_vocative

# revision identifiers, used by Alembic.
revision: str = "7f72e4368479"
down_revision: str | Sequence[str] | None = "fd6e48a7d821"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Recompute every normalized column with normalize_arabic, which now strips ۥ and ۦ."""
    connection = op.get_bind()

    segments = [
        {**row, "form_normalized": normalize_arabic(row["form"])}
        for row in connection.execute(
            sa.text(
                "SELECT id, word_id, form, kind, features FROM segments ORDER BY word_id, number"
            )
        ).mappings()
    ]
    words = {
        word_id: {"id": word_id, "split_normalized": split_vocative(list(rows))}
        for word_id, rows in groupby(segments, key=lambda row: row["word_id"])
    }
    for word_id, text_uthmani in connection.execute(sa.text("SELECT id, text_uthmani FROM words")):
        words[word_id]["text_normalized"] = normalize_arabic(text_uthmani)

    if segments:
        connection.execute(
            sa.text(
                "UPDATE segments SET form_normalized = v.form_normalized "
                "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) "
                "AS v(id integer, form_normalized text) WHERE segments.id = v.id"
            ),
            {
                "rows": json.dumps(
                    [{"id": s["id"], "form_normalized": s["form_normalized"]} for s in segments]
                )
            },
        )
        connection.execute(
            sa.text(
                "UPDATE words SET text_normalized = v.text_normalized, "
                "split_normalized = v.split_normalized "
                "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) "
                "AS v(id integer, text_normalized text, split_normalized text[]) "
                "WHERE words.id = v.id"
            ),
            {"rows": json.dumps(list(words.values()))},
        )


def downgrade() -> None:
    """Data-only change: the older normalization kept ۥ and ۦ, which was a search bug."""
