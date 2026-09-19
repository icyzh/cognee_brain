from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import store
from app.config import COGNEE_DATASET, COGNEE_SERVICE_URL


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    yield


app = FastAPI(title="Cognee Brain API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "cognee_version": version("cognee"),
        "cognee_configured": bool(COGNEE_SERVICE_URL),
        "dataset": COGNEE_DATASET,
        "llm_model": "tenant-managed",
    }
