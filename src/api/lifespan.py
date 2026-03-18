from contextlib import asynccontextmanager
from sqlalchemy import text

from db.database import Base, engine


@asynccontextmanager
async def lifespan(app):

    Base.metadata.create_all(bind=engine)
    print("-> DB created/verified succesfully.")

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            print("-> DB connection successful.")
    except Exception as e:
        print("-> DB connection failed.")

    yield

    engine.dispose()
    print("-> API shutdown.")
