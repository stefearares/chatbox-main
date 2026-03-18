from contextlib import asynccontextmanager
from sqlalchemy import text

from db.database import Base, engine


@asynccontextmanager
async def lifespan(app):
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    print("-> DB created/verified successfully.")

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            print("-> DB connection successful.")
    except Exception as e:
        print("-> DB connection failed. Exception:", e)

    yield

    engine.dispose()
    print("-> API shutdown.")
