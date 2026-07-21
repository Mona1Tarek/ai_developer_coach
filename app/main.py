from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from app.api.router import api_router
from app.core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(title="AI Developer Coach", lifespan=lifespan)
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "AI Developer Coach API"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
