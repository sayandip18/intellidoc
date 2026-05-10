from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.entity import Entity

EMBEDDING_DIMENSIONS = 1536  # OpenAI text-embedding-3-small


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_chunk"),)

    id: Mapped[str] = mapped_column(
        primary_key=True, default=generate_uuid
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True
    )
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    entities: Mapped[List["Entity"]] = relationship(
        "Entity", back_populates="source_chunk"
    )

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} document_id={self.document_id} index={self.chunk_index}>"