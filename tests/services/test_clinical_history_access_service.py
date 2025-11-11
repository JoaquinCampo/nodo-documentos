from __future__ import annotations

import pytest

from nodo_documentos.db.repos.clinical_history_access import (
    ClinicalHistoryAccessRepository,
)
from nodo_documentos.services.clinical_history_access_service import (
    ClinicalHistoryAccessService,
)


@pytest.mark.asyncio
async def test_log_access_attempt(async_session):
    repo = ClinicalHistoryAccessRepository(async_session)
    service = ClinicalHistoryAccessService(repo)

    entry = await service.log_access_attempt(
        health_user_ci="patient-1",
        health_worker_ci="worker-1",
        clinic_name="clinic-1",
        viewed=True,
        decision_reason="ALLOWED",
    )

    assert entry.viewed is True
    assert entry.decision_reason == "ALLOWED"
    entries = await service.list_access_attempts_for_health_user("patient-1")
    assert len(entries) == 1
    assert entries[0].id == entry.id


@pytest.mark.asyncio
async def test_list_access_attempts_orders_desc(async_session):
    repo = ClinicalHistoryAccessRepository(async_session)
    service = ClinicalHistoryAccessService(repo)

    first = await service.log_access_attempt(
        health_user_ci="patient-2",
        health_worker_ci="worker-1",
        clinic_name="clinic-1",
        viewed=False,
        decision_reason="DENIED",
    )
    second = await service.log_access_attempt(
        health_user_ci="patient-2",
        health_worker_ci="worker-1",
        clinic_name="clinic-1",
        viewed=True,
        decision_reason="ALLOWED",
    )

    entries = await service.list_access_attempts_for_health_user("patient-2")
    assert [entry.id for entry in entries] == [second.id, first.id]
    assert entries[0].decision_reason == "ALLOWED"
