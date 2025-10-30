from fastapi import APIRouter

# from nodo_documentos.api.routes import clinical_history, documents
from nodo_documentos.api.routes import mock_router

api_router = APIRouter()
# api_router.include_router(documents.router)
# api_router.include_router(clinical_history.router)
api_router.include_router(mock_router.router)
