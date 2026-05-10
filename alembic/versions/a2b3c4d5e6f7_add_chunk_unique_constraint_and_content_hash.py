"""add chunk unique constraint and document content_hash

Revision ID: a2b3c4d5e6f7
Revises: c27e06f7eb3e
Create Date: 2026-05-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'c27e06f7eb3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('content_hash', sa.Text(), nullable=True))
    op.create_unique_constraint('uq_documents_content_hash', 'documents', ['content_hash'])
    op.create_unique_constraint('uq_chunks_document_chunk', 'chunks', ['document_id', 'chunk_index'])


def downgrade() -> None:
    op.drop_constraint('uq_chunks_document_chunk', 'chunks', type_='unique')
    op.drop_constraint('uq_documents_content_hash', 'documents', type_='unique')
    op.drop_column('documents', 'content_hash')
