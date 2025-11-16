from fastapi import APIRouter, Depends

from nodo_documentos.api.dependencies import document_service
from nodo_documentos.api.schemas import CI, DocumentResponse
from nodo_documentos.services.document_service import DocumentService

router = APIRouter(prefix="/clinical-history", tags=["clinical-history"])


@router.get(
    "/{health_user_ci}",
    response_model=list[DocumentResponse],
)
async def fetch_clinical_history(
    health_user_ci: CI,
    documents: DocumentService = Depends(document_service),
) -> list[DocumentResponse]:
    """
    Fetch the clinical history for the given patient.

    Returns all documents associated with the specified health user CI.
    """

    documents_list = await documents.list_documents_for_health_user(health_user_ci)
    return [DocumentResponse.model_validate(doc) for doc in documents_list]
