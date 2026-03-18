from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import UserRecord
from utils.get_user import get_current_user
from utils.serializers import paginated_response, serialize_file
from api.services import files as files_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    content = await file.read()
    record = files_service.create_file_record(
        db,
        user_id=current_user.id,
        filename=file.filename,
        content=content,
        content_type=file.content_type,
    )

    return {**serialize_file(record), "path": record.path}


@router.get("")
def list_files(
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = files_service.list_files(db, user_id=current_user.id)
    return [serialize_file(r) for r in records]


@router.get("/search/chunks")
def search_chunks(
    q: str,
    limit: int = 10,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = files_service.search_chunks(
        db=db, user_id=current_user.id, query=q, limit=limit
    )
    return {"results": results}


@router.get("/search/fts")
def search_files_fts(
    q: str,
    limit: int = 10,
    offset: int = 0,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = files_service.search_files_fts(
        db=db, user_id=current_user.id, query=q, limit=limit, offset=offset
    )

    return paginated_response(
        results=[{**serialize_file(file), "rank": round(rank, 2)} for file, rank in results],
        offset=offset,
        limit=limit,
    )


@router.get("/search/semantic")
def search_files_semantic(
    q: str,
    limit: int = 10,
    offset: int = 0,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = files_service.search_files_semantic(
        db=db, user_id=current_user.id, query=q, limit=limit, offset=offset
    )

    return paginated_response(
        results=[{**serialize_file(file), "distance": distance} for file, distance in results],
        offset=offset,
        limit=limit,
    )


@router.get("/search")
def search_files(
    q: str,
    limit: int = 10,
    offset: int = 0,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = files_service.search_files(
        db=db, user_id=current_user.id, query=q, limit=limit, offset=offset
    )

    return paginated_response(
        results=[{**serialize_file(file), "rank": round(rank, 2)} for file, rank in results],
        offset=offset,
        limit=limit,
    )


@router.get("/{file_id}")
def get_file(
    file_id: int,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = files_service.get_file(db, file_id=file_id, user_id=current_user.id)
    return serialize_file(record)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    files_service.delete_file(db, file_id=file_id, user_id=current_user.id)


@router.get("/{file_id}/content")
def get_file_content(
    file_id: int,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = files_service.get_file(db, file_id=file_id, user_id=current_user.id)

    file_path = Path(record.path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk"
        )

    return FileResponse(
        path=str(file_path),
        media_type=record.content_type,
        filename=record.original_name,
    )
