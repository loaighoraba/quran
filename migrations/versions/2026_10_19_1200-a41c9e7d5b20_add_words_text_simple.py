"""add words text_simple

Revision ID: a41c9e7d5b20
Revises: 7f72e4368479
Create Date: 2026-10-19 12:00:00.000000

"""

import json
from collections.abc import Sequence
from itertools import groupby

import sqlalchemy as sa
from alembic import op

from app.scripts.morphology import pair_simple_words

# revision identifiers, used by Alembic.
revision: str = "a41c9e7d5b20"
down_revision: str | Sequence[str] | None = "7f72e4368479"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("words", sa.Column("text_simple", sa.Text(), nullable=True))
    # Backfill from the ayas already loaded, with the loader's own pairing function
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT w.id, w.aya_id, a.text_simple AS aya_text, "
            "cardinality(w.split_normalized) AS n "
            "FROM words w JOIN ayas a ON a.id = w.aya_id ORDER BY w.aya_id, w.number"
        )
    ).mappings()
    words = []
    for _, group in groupby(rows, key=lambda row: row["aya_id"]):
        aya_words = list(group)
        spellings = pair_simple_words(aya_words[0]["aya_text"], [row["n"] for row in aya_words])
        words.extend(
            {"id": row["id"], "text_simple": s} for row, s in zip(aya_words, spellings, strict=True)
        )
    if words:
        connection.execute(
            sa.text(
                "UPDATE words SET text_simple = v.text_simple "
                "FROM jsonb_to_recordset(CAST(:words AS jsonb)) "
                "AS v(id integer, text_simple text) WHERE words.id = v.id"
            ),
            {"words": json.dumps(words)},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("words", "text_simple")
