from fastapi import APIRouter

from nodo_documentos.api.routes import chat, clinical_history, documents

api_router = APIRouter()
api_router.include_router(documents.router)
api_router.include_router(clinical_history.router)
api_router.include_router(chat.router)
