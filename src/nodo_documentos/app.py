from fastapi import FastAPI

from nodo_documentos.api.middleware import APIKeyMiddleware
from nodo_documentos.api.router import api_router
from nodo_documentos.utils.settings import api_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Prestadores de Salud", version="0.1.0")
    if api_settings.key:
        app.add_middleware(
            APIKeyMiddleware,
            api_key=api_settings.key,
            header_name=api_settings.header_name,
        )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
