from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.document import Document


class EntityType:
    PERSON = "PERSON"
    ORG = "ORG"
    DATE = "DATE"
    LOCATION = "LOCATION"
    CLAUSE = "CLAUSE"
    KEYWORD = "KEYWORD"


class Entity(Base, TimestampMixin):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=generate_uuid
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_chunk_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # relationships
    document: Mapped["Document"] = relationship("Document", back_populates="entities")
    source_chunk: Mapped[Optional["Chunk"]] = relationship(
        "Chunk", back_populates="entities"
    )

    def __repr__(self) -> str:
        return f"<Entity id={self.id} type={self.entity_type} value={self.value}>"