from __future__ import annotations

import pytest

from nodo_documentos.db.repos.document import DocumentRepository
from nodo_documentos.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_create_document(async_session):
    repo = DocumentRepository(async_session)
    service = DocumentService(repo)

    created = await service.create_document(
        created_by="worker-1",
        health_user_ci="patient-1",
        clinic_id="clinic-1",
        s3_url="s3://bucket/doc",
    )

    assert created.created_by == "worker-1"
    docs = await service.list_documents_for_health_user("patient-1")
    assert len(docs) == 1
    assert docs[0].doc_id == created.doc_id


@pytest.mark.asyncio
async def test_list_documents_orders_desc(async_session):
    repo = DocumentRepository(async_session)
    service = DocumentService(repo)

    first = await service.create_document(
        created_by="worker-1",
        health_user_ci="patient-2",
        clinic_id="clinic-1",
        s3_url="s3://bucket/doc-1",
    )
    second = await service.create_document(
        created_by="worker-1",
        health_user_ci="patient-2",
        clinic_id="clinic-1",
        s3_url="s3://bucket/doc-2",
    )

    docs = await service.list_documents_for_health_user("patient-2")
    assert [doc.doc_id for doc in docs] == [second.doc_id, first.doc_id]
