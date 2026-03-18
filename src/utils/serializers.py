from db.models import FileRecord


def serialize_file(record: FileRecord) -> dict:
    return {
        "id": record.id,
        "filename": record.original_name,
        "content_type": record.content_type,
        "size": record.size,
        "created_at": record.created_at,
    }


def paginated_response(results: list, offset: int, limit: int) -> dict:
    return {"offset": offset, "limit": limit, "results": results}
