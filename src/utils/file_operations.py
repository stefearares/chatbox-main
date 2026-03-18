import uuid
from pathlib import Path

UPLOAD_DIR = Path("files")


def save_upload_file(file_content: bytes, filename: str, user_id: int) -> dict:
    # 1. Handle directory
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    # We keep the extension but randomize the base name
    extension = Path(filename).suffix
    random_name = f"{uuid.uuid4()}{extension}"

    dest = user_dir / random_name

    # 3. Write to disk
    dest.write_bytes(file_content)

    return {"random_name": random_name, "original_name": filename, "path": str(dest)}
