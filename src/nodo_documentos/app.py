from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
import sys
import traceback
from pathlib import Path

# Add src directory to Python path for Vercel
# Vercel runs from /var/task/src/nodo_documentos/app.py
# We need to add /var/task/src to sys.path so imports work
# Path(__file__) = /var/task/src/nodo_documentos/app.py
# .parent = /var/task/src/nodo_documentos/
# .parent.parent = /var/task/src/
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
    # Debug: log the path we added (will appear in Vercel logs)
    try:
        import logging
        logging.basicConfig(level=logging.INFO)
        logging.info(f"Added to sys.path: {src_path}")
        logging.info(f"Current sys.path: {sys.path[:3]}")
    except Exception:
        pass

# Configure loguru to output to stderr (Vercel captures this)
# Use try/except to prevent logger configuration from crashing the app
try:
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
    )
except Exception:
    # If logger configuration fails, continue without custom logging
    pass

# Only load .env file if it exists (for local development)
# On Vercel, environment variables are set directly
try:
    load_dotenv(override=False)
except Exception:
    pass


def create_app() -> FastAPI:
    try:
        # Import here to avoid import-time failures
        from nodo_documentos.api.middleware import APIKeyMiddleware
        from nodo_documentos.api.router import api_router
        from nodo_documentos.utils.settings import api_settings
        
        app = FastAPI(title="Documentos Clinicos", version="0.1.0")
        
        # Global exception handler - must be simple to avoid recursion
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            try:
                error_trace = traceback.format_exc()
                logger.error(f"Unhandled exception: {exc}\n{error_trace}")
            except Exception:
                # If logging fails, continue anyway
                pass
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error": str(exc),
                    "type": type(exc).__name__,
                },
            )
        
        # Health check endpoint that doesn't require any dependencies
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
        return app
    except Exception as e:
        error_trace = traceback.format_exc()
        error_msg = str(e)
        error_type = type(e).__name__
        try:
            logger.error(f"Error in create_app: {e}\n{error_trace}")
        except Exception:
            pass
        # Return a minimal app that shows the error
        # Capture error details in local variables to avoid closure issues
        error_app = FastAPI(title="Documentos Clinicos", version="0.1.0")
        
        @error_app.get("/{path:path}")
        async def error_handler(request: Request):
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Application initialization failed",
                    "error": error_msg,
                    "type": error_type,
                },
            )
        return error_app


# Always ensure we have a valid app object
# Capture error in a way that's accessible to the error handler
_init_error = None
try:
    app = create_app()
except Exception as e:
    error_trace = traceback.format_exc()
    _init_error = e
    error_msg = str(e)
    error_type = type(e).__name__
    try:
        logger.error(f"Failed to create app: {e}\n{error_trace}")
    except Exception:
        pass
    # Create a minimal app that can at least respond with errors
    app = FastAPI(title="Documentos Clinicos", version="0.1.0")
    
    @app.get("/{path:path}")
    async def error_handler(request: Request):
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Application initialization failed",
                "error": error_msg,
                "type": error_type,
            },
        )
