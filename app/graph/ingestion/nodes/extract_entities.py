"""
Runs Named Entity Recognition (NER) over every chunk using spaCy's
en_core_web_sm model and accumulates a flat list of ExtractedEntity
objects keyed by (chunk_index, label, text).
"""

from __future__ import annotations

import logging
from typing import Iterable

import spacy
from spacy.tokens import Span

from app.graph.ingestion.state import ExtractedEntity, IngestionState, IngestionStatus

logger = logging.getLogger(__name__)

_KEEP_LABELS: frozenset[str] = frozenset({
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "PRODUCT",
    "EVENT",
    "LAW",
    "DATE",
    "MONEY",
    "NORP",
    "WORK_OF_ART",
    "FAC",
})

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        logger.info("extract_entities | loading spaCy model en_core_web_sm")
        _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
    return _nlp


def _deduplicate(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    seen: set[tuple[int, str, str]] = set()
    result: list[ExtractedEntity] = []
    for ent in entities:
        key = (ent["chunk_index"], ent["label"], ent["text"].lower())
        if key not in seen:
            seen.add(key)
            result.append(ent)
    return result


def _spans_to_entities(spans: Iterable[Span], chunk_index: int) -> list[ExtractedEntity]:
    return [
        ExtractedEntity(
            text=span.text.strip(),
            label=span.label_,
            chunk_index=chunk_index,
        )
        for span in spans
        if span.label_ in _KEEP_LABELS and span.text.strip()
    ]


def extract_entities(state: IngestionState) -> dict:
    logger.info("extract_entities | doc_id=%s", state["document_id"])

    chunks = state.get("chunks", [])
    if not chunks:
        msg = "extract_entities received no chunks."
        logger.warning(msg)
        return {
            "entities":   [],
            "status":     IngestionStatus.STORING,
            "node_trace": ["extract_entities"],
        }

    nlp = _get_nlp()
    texts = [doc.page_content for doc in chunks]

    all_entities: list[ExtractedEntity] = []

    for chunk_index, spacy_doc in enumerate(nlp.pipe(texts, batch_size=32)):
        chunk_entities = _spans_to_entities(spacy_doc.ents, chunk_index)
        all_entities.extend(chunk_entities)

    all_entities = _deduplicate(all_entities)

    logger.info(
        "extract_entities | doc_id=%s  entities=%d",
        state["document_id"],
        len(all_entities),
    )

    return {
        "entities":   all_entities,
        "status":     IngestionStatus.STORING,
        "node_trace": ["extract_entities"],
    }
