from nodo_documentos.db.models import ClinicalHistoryAccessLog
from nodo_documentos.db.repos.clinical_history_access import (
    ClinicalHistoryAccessRepository,
)


class ClinicalHistoryAccessService:
    """Coordinates audit logging for history access attempts."""

    def __init__(self, access_repo: ClinicalHistoryAccessRepository) -> None:
        self._access_repo = access_repo

    async def log_access_attempt(
        self,
        *,
        health_user_ci: str,
        health_worker_ci: str,
        clinic_id: str,
        viewed: bool,
        decision_reason: str | None,
    ) -> ClinicalHistoryAccessLog:
        """Persist the outcome of a clinical history authorization."""
        return await self._access_repo.log_access(
            health_user_ci=health_user_ci,
            health_worker_ci=health_worker_ci,
            clinic_id=clinic_id,
            viewed=viewed,
            decision_reason=decision_reason,
        )

    async def list_access_attempts_for_health_user(
        self, health_user_ci: str
    ) -> list[ClinicalHistoryAccessLog]:
        """Fetch audit entries for a patient ordered from newest to oldest."""

        return await self._access_repo.list_by_health_user(health_user_ci)

    async def list_access_attempts_for_health_worker(
        self,
        health_worker_ci: str,
        health_user_ci: str | None = None,
    ) -> list[ClinicalHistoryAccessLog]:
        """Fetch audit entries for a health worker ordered from newest to oldest."""

        return await self._access_repo.list_by_health_worker(
            health_worker_ci, health_user_ci
        )
