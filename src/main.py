from fastapi import FastAPI
import uvicorn
from api.lifespan import lifespan
from api.routes import core_router, auth_router, files_router

app = FastAPI(lifespan=lifespan)

app.include_router(core_router)
app.include_router(auth_router)
app.include_router(files_router)


def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
