import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

# Add src directory to Python path for Vercel
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Configure loguru to output to stderr (Vercel captures this)
logger.remove()
logger.add(
    sys.stderr,
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
    level="DEBUG",
)

# Load .env file for local development (Vercel uses environment variables)
load_dotenv(override=False)

# Imports after sys.path manipulation for Vercel compatibility
from nodo_documentos.api.middleware import APIKeyMiddleware  # noqa: E402
from nodo_documentos.api.router import api_router  # noqa: E402
from nodo_documentos.utils.settings import api_settings  # noqa: E402

app = FastAPI(title="Documentos Clinicos", version="0.1.0")


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}\n{error_trace}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "type": type(exc).__name__,
        },
    )


@app.get("/")
async def root():
    return {"status": "ok", "service": "nodo-documentos"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if api_settings.key:
    app.add_middleware(
        APIKeyMiddleware,
        api_key=api_settings.key,
        header_name=api_settings.header_name,
    )

app.include_router(api_router, prefix="/api")
