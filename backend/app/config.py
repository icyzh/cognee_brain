import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(os.environ.get("DATA_DIR", BACKEND_DIR.parent / "data"))
APP_DB = Path(os.environ.get("APP_DB", BACKEND_DIR / "app.db"))
COGNEE_SERVICE_URL = os.environ.get("COGNEE_SERVICE_URL", "").rstrip("/")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")
COGNEE_DATASET = os.environ.get("COGNEE_DATASET", "acme")
