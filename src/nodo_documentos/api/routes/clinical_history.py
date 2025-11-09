from fastapi import APIRouter, Depends, Query

from nodo_documentos.api.dependencies import (
    clinical_history_access_service,
    document_service,
)
from nodo_documentos.api.schemas import CI, DocumentResponse
from nodo_documentos.services.clinical_history_access_service import (
    ClinicalHistoryAccessService,
)
from nodo_documentos.services.document_service import DocumentService

router = APIRouter(prefix="/clinical-history", tags=["clinical-history"])


@router.get(
    "/{health_user_ci}",
    response_model=list[DocumentResponse],
)
async def fetch_clinical_history(
    health_user_ci: CI,
    health_worker_ci: CI = Query(..., description="Worker requesting the history"),
    clinic_name: str = Query(..., description="Clinic requesting the history"),
    documents: DocumentService = Depends(document_service),
    access_logs: ClinicalHistoryAccessService = Depends(
        clinical_history_access_service
    ),
) -> list[DocumentResponse]:
    """
    Fetch the clinical history for the given patient after consulting the HCEN
    authorization service. Every attempt is logged regardless of the outcome.
    """

    await access_logs.log_access_attempt(
        health_user_ci=health_user_ci,
        health_worker_ci=health_worker_ci,
        clinic_id=clinic_name,
        viewed=True,
        decision_reason=None,
    )

    documents_list = await documents.list_documents_for_health_user(health_user_ci)
    return [DocumentResponse.model_validate(doc) for doc in documents_list]
