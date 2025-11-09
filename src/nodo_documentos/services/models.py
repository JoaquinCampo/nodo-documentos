from pydantic import Field

from nodo_documentos.rag.chunking.models import Chunk


class ClinicalDocumentChunk(Chunk):
    """
    Clinical document chunk with ownership metadata.

    Extends the base Chunk model with clinical document ownership information
    for access control and auditing in vector search results.
    """

    # Business ownership fields
    document_id: str = Field(
        description="SQL Document.doc_id - links to clinical record"
    )
    health_user_ci: str = Field(description="Patient CI - who the document belongs to")
    clinic_id: str = Field(description="Clinic ID - which clinic manages the document")
    created_by: str = Field(description="Uploader CI - who uploaded the document")
