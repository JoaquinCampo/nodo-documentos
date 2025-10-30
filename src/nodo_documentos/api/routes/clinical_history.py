from fastapi import APIRouter, Depends, HTTPException, Query, status

from nodo_documentos.api.dependencies import (
    authorization_service,
    clinical_history_access_service,
    document_service,
)
from nodo_documentos.api.schemas import CI, DocumentResponse, UUIDStr
from nodo_documentos.services.authorization_service import AuthorizationService
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
    clinic_id: UUIDStr = Query(..., description="Clinic requesting the history"),
    documents: DocumentService = Depends(document_service),
    access_logs: ClinicalHistoryAccessService = Depends(
        clinical_history_access_service
    ),
    authorizer: AuthorizationService = Depends(authorization_service),
) -> list[DocumentResponse]:
    """
    Fetch the clinical history for the given patient after consulting the HCEN
    authorization service. Every attempt is logged regardless of the outcome.
    """

    decision = await authorizer.can_view_clinical_history(
        health_user_ci=health_user_ci,
        health_worker_ci=health_worker_ci,
        clinic_id=clinic_id,
    )

    await access_logs.log_access_attempt(
        health_user_ci=health_user_ci,
        health_worker_ci=health_worker_ci,
        clinic_id=clinic_id,
        viewed=decision.allowed,
        decision_reason=decision.reason,
    )

    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=decision.reason or "Access to clinical history denied",
        )

    documents_list = await documents.list_documents_for_health_user(health_user_ci)
    return [DocumentResponse.model_validate(doc) for doc in documents_list]
