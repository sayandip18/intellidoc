"""
Runs Named Entity Recognition (NER) over every chunk using spaCy's
en_core_web_sm model and accumulates a flat list of ExtractedEntity
objects keyed by (chunk_index, label, text).

Entities are stored alongside chunks in the metadata store and can be
used later for filtered retrieval (e.g. "find all chunks mentioning Acme Corp").
"""

from __future__ import annotations

import logging
from typing import Iterable

import spacy
from spacy.tokens import Span

from state import ExtractedEntity, IngestionState, IngestionStatus

logger = logging.getLogger(__name__)

# Entity labels we care about — filter out noise (e.g. CARDINAL, ORDINAL)
_KEEP_LABELS: frozenset[str] = frozenset({
    "PERSON",
    "ORG",
    "GPE",        # countries, cities, states
    "LOC",        # non-GPE locations
    "PRODUCT",
    "EVENT",
    "LAW",
    "DATE",
    "MONEY",
    "NORP",       # nationalities, religious/political groups
    "WORK_OF_ART",
    "FAC",        # buildings, airports, etc.
})


# ---------------------------------------------------------------------------
# Lazy-load spaCy model (once per worker process)
# ---------------------------------------------------------------------------

_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        logger.info("extract_entities | loading spaCy model en_core_web_sm")
        _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
    return _nlp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deduplicate(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    """
    Remove duplicate (chunk_index, label, text) triples that spaCy
    sometimes produces from overlapping noun chunks.
    """
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


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def extract_entities(state: IngestionState) -> dict:
    """
    LangGraph node — extract_entities.

    Uses spaCy pipe() for efficient batch NER across all chunks.
    Returns state['entities'] as an accumulated list (operator.add reducer
    is defined on this field in IngestionState, so multiple node invocations
    would append rather than overwrite — useful if this node is ever fanned out).
    """
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

    # spaCy pipe() processes texts in mini-batches internally
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