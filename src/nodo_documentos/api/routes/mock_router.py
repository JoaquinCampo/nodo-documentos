from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/mock", tags=["mock"])


DOCUMENTOS = {
    "ae3f82b4-0f31-483e-8227-34901a17222e": {
        "health_user_ci": "12345678",
        "title": "Radiografía de tórax",
        "created_at": "2025-10-29T00:00:00Z",
        "s3_url": "s3://bucket/doc-1",
    },
    "ae3f82b4-0f31-483e-8227-34901a17222f": {
        "health_user_ci": "87654321",
        "title": "Análisis de sangre",
        "created_at": "2025-02-20T00:00:00Z",
        "s3_url": "s3://bucket/doc-2",
    },
}


@router.get("/documents")
async def get_documents():
    """
    Retrieve all mock clinical documents registered in the simulated health provider.

    This endpoint emulates the interface of a *Prestador de Salud* (health provider)
    within the HCEN ecosystem. It returns a static collection of clinical document
    metadata, representing documents stored locally by the provider. Each document
    includes identifying information and a reference to its storage location.

    Returns:
        dict: A dictionary where each key is a unique document identifier (UUID),
        and each value is a JSON object containing:
            - **health_user_ci** (`str`): Citizen ID of the health user (Uruguayan CI).
            - **title** (`str`): Title or short description of the clinical document.
            - **created_at** (`str`, ISO 8601): Document creation date and time.
            - **s3_url** (`str`): Simulated S3 storage path for the document.

    Example response:
    ```json
    {
      "ae3f82b4-0f31-483e-8227-34901a17222e": {
        "health_user_ci": "12345678",
        "title": "Radiografía de tórax",
        "created_at": "2025-10-29T00:00:00Z",
        "s3_url": "s3://bucket/doc-1"
      },
      "ae3f82b4-0f31-483e-8227-34901a17222f": {
        "health_user_ci": "87654321",
        "title": "Análisis de sangre",
        "created_at": "2025-02-20T00:00:00Z",
        "s3_url": "s3://bucket/doc-2"
      }
    }
    ```

    """
    return DOCUMENTOS


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """
    Retrieve a specific clinical document by its unique identifier.

    This endpoint simulates the operation used by the HCEN Central component
    to obtain a clinical document stored in a health provider system.
    """
    document = DOCUMENTOS.get(document_id)
    if not document:
        return {"error": "Document not found"}
    return document


@router.get("/documents/patient/{health_user_ci}")
async def get_documents_by_user(health_user_ci: str):
    """
    Retrieve all clinical documents belonging to a given health user (patient).

    Args:
        health_user_ci (str): National ID (CI) of the health user.

    Returns:
        dict: All documents associated with that user.
    """
    return {
        k: v for k, v in DOCUMENTOS.items() if v["health_user_ci"] == health_user_ci
    }


class DocumentCreate(BaseModel):
    health_user_ci: str
    title: str
    created_at: str
    s3_url: str


@router.post("/documents/register")
async def register_document(doc: DocumentCreate):
    """
    Register a new clinical document in the mock provider.

    This simulates a professional uploading a new clinical document.
    """
    import uuid

    doc_id = str(uuid.uuid4())
    DOCUMENTOS[doc_id] = doc.dict()
    return {"message": "Document registered", "id": doc_id}


@router.get("/status")
async def status():
    """Check the health status of the mock provider service."""
    return {"status": "ok", "documents": len(DOCUMENTOS)}
