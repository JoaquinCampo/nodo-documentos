import pytest

from nodo_documentos.db.repos.clinical_history_access import (
    ClinicalHistoryAccessRepository,
)


@pytest.mark.asyncio
async def test_log_access_persists_attempt(async_session):
    repo = ClinicalHistoryAccessRepository(async_session)

    entry = await repo.log_access(
        health_user_ci="patient-1",
        health_worker_ci="worker-777",
        clinic_name="clinic-2",
        viewed=True,
        decision_reason="ALLOWED",
    )

    assert entry.id is not None
    assert entry.viewed is True
    assert entry.decision_reason == "ALLOWED"

    entries = await repo.list_by_health_user("patient-1")
    assert len(entries) == 1
    assert entries[0].id == entry.id


@pytest.mark.asyncio
async def test_list_by_health_user_orders_desc(async_session):
    repo = ClinicalHistoryAccessRepository(async_session)

    first = await repo.log_access(
        health_user_ci="patient-2",
        health_worker_ci="worker-1",
        clinic_name="clinic-2",
        viewed=False,
        decision_reason="DENIED",
    )
    second = await repo.log_access(
        health_user_ci="patient-2",
        health_worker_ci="worker-1",
        clinic_name="clinic-2",
        viewed=True,
        decision_reason="ALLOWED",
    )

    entries = await repo.list_by_health_user("patient-2")
    assert [entry.id for entry in entries] == [second.id, first.id]
    assert entries[0].decision_reason == "ALLOWED"
