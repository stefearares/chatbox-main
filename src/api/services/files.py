from pathlib import Path
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import Float, func, desc
from sqlalchemy import cast as sa_cast
from sqlalchemy.orm import Session

from db.models import ChunkRecord, FileContentRecord, FileRecord
from utils import file_operations
from utils.chunking import chunk_by_sentence, embed


def create_file_record(
    db: Session,
    user_id: int,
    filename: str,
    content: bytes,
    content_type: str,
) -> FileRecord:
    mime = (content_type or "application/octet-stream").split(";")[0].strip()
    if not mime.startswith("text/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Only text files allowed. Got: '{mime}'",
        )

    try:
        file_info = file_operations.save_upload_file(
            file_content=content, filename=filename, user_id=user_id
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file to disk.",
        )

    record = FileRecord(
        user_id=user_id,
        original_name=file_info["original_name"],
        stored_name=file_info["random_name"],
        path=file_info["path"],
        content_type=content_type or "application/octet-stream",
        size=len(content),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        text_content = content.decode("utf-8", errors="ignore")
    except Exception:
        text_content = ""

    if not text_content:
        return record

    # Full-text search index
    db.add(FileContentRecord(
        file_id=record.id,
        content_tsv=func.to_tsvector("english", text_content),
    ))

    # Chunk and embed — if Voyage fails we roll back chunks/content but keep the file record
    chunks = chunk_by_sentence(text_content)
    try:
        embeddings = embed(chunks)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding service unavailable. File was saved but not indexed.",
        )

    for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings), start=1):
        db.add(ChunkRecord(file_id=record.id, chunk_index=i, text=chunk_text, embedding=emb))

    db.commit()
    return record


def get_file(db: Session, file_id: int, user_id: int) -> FileRecord:
    record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id, FileRecord.user_id == user_id)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return record


def list_files(db: Session, user_id: int) -> List[FileRecord]:
    return db.query(FileRecord).filter(FileRecord.user_id == user_id).all()


def reciprocal_rank_fusion(
    *ranked_lists: List[FileRecord], k: int = 60
) -> dict[int, dict]:
    scores: dict[int, dict] = {}
    for ranked in ranked_lists:
        for rank, file in enumerate(ranked, start=1):
            if file.id not in scores:
                scores[file.id] = {"file": file, "score": 0.0}
            scores[file.id]["score"] += 1.0 / (k + rank)
    return scores


def search_files(
    db: Session, user_id: int, query: str, limit: int = 10, offset: int = 0
):
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty."
        )

    pool = limit * 3

    ts_query = func.websearch_to_tsquery("english", query)
    fts_files: List[FileRecord] = (
        db.query(FileRecord)
        .join(FileContentRecord, FileContentRecord.file_id == FileRecord.id)
        .filter(
            FileRecord.user_id == user_id,
            FileContentRecord.content_tsv.op("@@")(ts_query),
        )
        .order_by(desc(func.ts_rank(FileContentRecord.content_tsv, ts_query)))
        .limit(pool)
        .all()
    )

    try:
        query_vec = embed([query])[0]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding service unavailable.",
        )

    raw_vec = (
        db.query(FileRecord)
        .join(ChunkRecord, ChunkRecord.file_id == FileRecord.id)
        .filter(FileRecord.user_id == user_id)
        .order_by(sa_cast(ChunkRecord.embedding.op("<=>")(query_vec), Float))
        .limit(pool * 5)
        .all()
    )

    seen: set[int] = set()
    vec_files: List[FileRecord] = []
    for file in raw_vec:
        if file.id not in seen:
            seen.add(file.id)
            vec_files.append(file)

    scores = reciprocal_rank_fusion(fts_files, vec_files)
    sorted_results = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

    return [(item["file"], round(item["score"], 4)) for item in sorted_results[offset: offset + limit]]


def search_files_fts(
    db: Session, user_id: int, query: str, limit: int = 10, offset: int = 0
):
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty."
        )

    ts_query = func.websearch_to_tsquery("english", query)
    rank = (func.ts_rank(FileContentRecord.content_tsv, ts_query) * 100).label("rank")

    return (
        db.query(FileRecord, rank)
        .join(FileContentRecord, FileContentRecord.file_id == FileRecord.id)
        .filter(
            FileRecord.user_id == user_id,
            FileContentRecord.content_tsv.op("@@")(ts_query),
        )
        .order_by(desc(rank))
        .limit(limit)
        .offset(offset)
        .all()
    )


def search_files_semantic(
    db: Session, user_id: int, query: str, limit: int = 10, offset: int = 0
):
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty."
        )

    try:
        query_vec = embed([query])[0]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding service unavailable.",
        )

    raw = (
        db.query(FileRecord, sa_cast(ChunkRecord.embedding.op("<=>")(query_vec), Float).label("distance"))
        .join(ChunkRecord, ChunkRecord.file_id == FileRecord.id)
        .filter(FileRecord.user_id == user_id)
        .order_by("distance")
        .limit((offset + limit) * 5)
        .all()
    )

    seen: set[int] = set()
    unique: list[tuple] = []
    for file, distance in raw:
        if file.id not in seen:
            seen.add(file.id)
            unique.append((file, round(distance, 4)))

    return unique[offset: offset + limit]


def delete_file(db: Session, file_id: int, user_id: int) -> None:
    record = get_file(db, file_id, user_id)

    Path(record.path).unlink(missing_ok=True)
    db.delete(record)
    db.commit()
