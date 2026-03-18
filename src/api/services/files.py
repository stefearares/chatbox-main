from pathlib import Path
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from db.models import FileContentRecord, FileRecord
from utils import file_operations


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

    file_info = file_operations.save_upload_file(
        file_content=content, filename=filename, user_id=user_id
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

    if text_content:
        content_record = FileContentRecord(
            file_id=record.id,
            content_tsv=func.to_tsvector("english", text_content),
        )
        db.add(content_record)
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


def search_files(
    db: Session, user_id: int, query: str, limit: int = 10, offset: int = 0
):
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


def delete_file(db: Session, file_id: int, user_id: int) -> None:
    record = get_file(db, file_id, user_id)

    Path(record.path).unlink(missing_ok=True)
    db.delete(record)
    db.commit()
