"""split_normalized from text_simple

Revision ID: c7d2e4f81a63
Revises: a41c9e7d5b20
Create Date: 2026-10-19 15:00:00.000000

"""

import json
from collections.abc import Sequence
from itertools import groupby

import sqlalchemy as sa
from alembic import op

from app.arabic import normalize_arabic
from app.scripts.morphology import split_vocative

# revision identifiers, used by Alembic.
revision: str = "c7d2e4f81a63"
down_revision: str | Sequence[str] | None = "a41c9e7d5b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _update(words: list[dict]) -> None:
    if words:
        op.get_bind().execute(
            sa.text(
                "UPDATE words SET split_normalized = v.split_normalized "
                "FROM jsonb_to_recordset(CAST(:words AS jsonb)) "
                "AS v(id integer, split_normalized text[]) WHERE words.id = v.id"
            ),
            {"words": json.dumps(words)},
        )


def upgrade() -> None:
    """Spell the alef out in split_normalized, taking it from the simple-script spelling."""
    rows = op.get_bind().execute(
        sa.text("SELECT id, text_simple FROM words WHERE text_simple IS NOT NULL")
    )
    _update(
        [
            {"id": word_id, "split_normalized": [normalize_arabic(w) for w in simple.split(" ")]}
            for word_id, simple in rows
        ]
    )


def downgrade() -> None:
    """Rebuild split_normalized from the Uthmani segments."""
    segments = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT word_id, form_normalized, kind, features "
                "FROM segments ORDER BY word_id, number"
            )
        )
        .mappings()
    )
    _update(
        [
            {"id": word_id, "split_normalized": split_vocative(list(rows))}
            for word_id, rows in groupby(segments, key=lambda row: row["word_id"])
        ]
    )
