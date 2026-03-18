import re

import voyageai

from config.settings import settings

voyage_client = voyageai.Client(api_key=settings.voyage_key)

VOYAGE_MODEL = "voyage-3"
VOYAGE_DIMENSIONS = 1024


def chunk_by_char(text: str, chunk_size: int = 150, chunk_overlap: int = 20) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - chunk_overlap if end < len(text) else len(text)
    return chunks


def chunk_by_section(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"\n##", text) if s.strip()]


def chunk_by_sentence(text: str, max_sentences: int = 3, overlap: int = 1) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s", text.strip())
    chunks = []
    start = 0
    while start < len(sentences):
        end = min(start + max_sentences, len(sentences))
        chunks.append(" ".join(sentences[start:end]))
        start += max_sentences - overlap
        if start < 0:
            start = 0
    return chunks


def embed(texts: list[str]) -> list[list[float]]:
    result = voyage_client.embed(texts, model=VOYAGE_MODEL)
    return result.embeddings
