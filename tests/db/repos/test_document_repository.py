import pytest

from nodo_documentos.db.repos.document import DocumentRepository


@pytest.mark.asyncio
async def test_create_document_persists_entry(async_session):
    repo = DocumentRepository(async_session)

    created = await repo.create(
        created_by="worker-123",
        health_user_ci="patient-1",
        clinic_name="clinic-9",
        s3_url="s3://bucket/key-1",
    )

    assert created.doc_id is not None
    assert created.created_by == "worker-123"
    assert created.health_user_ci == "patient-1"

    docs = await repo.list_by_health_user("patient-1")
    assert len(docs) == 1
    assert docs[0].doc_id == created.doc_id


@pytest.mark.asyncio
async def test_list_by_health_user_returns_descending(async_session):
    repo = DocumentRepository(async_session)

    first = await repo.create(
        created_by="worker-1",
        health_user_ci="patient-1",
        clinic_name="clinic-1",
        s3_url="s3://bucket/doc-1",
    )
    second = await repo.create(
        created_by="worker-1",
        health_user_ci="patient-1",
        clinic_name="clinic-1",
        s3_url="s3://bucket/doc-2",
    )

    docs = await repo.list_by_health_user("patient-1")
    assert [doc.doc_id for doc in docs] == [second.doc_id, first.doc_id]
