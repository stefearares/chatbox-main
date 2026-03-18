import signal
import sys

from groq import Groq
from sqlalchemy import Float
from sqlalchemy import cast as sa_cast

from src.config.settings import settings
from src.db.database import Session
from src.db.models import ChunkRecord, FileRecord, UserRecord
from src.utils.chunking import embed
from src.utils.security import verify_password

groq_client = Groq(api_key=settings.groq_key)

GROQ_MODEL = "llama-3.1-8b-instant"
TOP_K = 5


def retrieve_chunks(query: str, user_id: int) -> list[dict]:
    query_vec = embed([query])[0]

    db = Session()
    try:
        results = (
            db.query(
                ChunkRecord.text,
                FileRecord.original_name,
                sa_cast(ChunkRecord.embedding.op("<=>")(query_vec), Float).label("distance"),
            )
            .join(FileRecord, FileRecord.id == ChunkRecord.file_id)
            .filter(FileRecord.user_id == user_id)
            .order_by("distance")
            .limit(TOP_K)
            .all()
        )
    finally:
        db.close()

    return [
        {"text": text, "filename": filename, "distance": round(distance, 4)}
        for text, filename, distance in results
    ]


def ask(query: str, user_id: int) -> str:
    chunks = retrieve_chunks(query, user_id)

    if not chunks:
        return "No relevant documents found."

    context = "\n\n".join(
        f"[{c['filename']}] {c['text']}" for c in chunks
    )

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer the user's question using only "
                    "the provided context. If the answer is not in the context, say so."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            },
        ],
    )

    return response.choices[0].message.content


def authenticate() -> UserRecord:
    db = Session()
    try:
        email = input("Email: ").strip()
        password = input("Password: ").strip()

        user = db.query(UserRecord).filter(UserRecord.email == email).first()
        if not user or not user.password_hash or not verify_password(user.password_hash, password):
            print("Invalid email or password.")
            sys.exit(1)

        return user
    except KeyboardInterrupt:
        goodbye()
    finally:
        db.close()


def goodbye(name: str = ""):
    print(f"\nGoodbye, {name}!" if name else "\nGoodbye!")
    sys.exit(0)


BANNER = """
    chatbox ai  *  v0.1
  =============================
  > ask anything about your files
"""


def main():
    print(BANNER)
    user = authenticate()
    signal.signal(signal.SIGTERM, lambda *_: goodbye(user.name))
    print(f"\nWelcome, {user.name}!\n")

    try:
        while True:
            query = input("> ").strip()
            if query.lower() == "/exit":
                goodbye(user.name)
            if not query:
                continue
            print("\nchatbox_ai: " + ask(query, user.id))
            print()
    except KeyboardInterrupt:
        goodbye(user.name)


if __name__ == "__main__":
    main()
