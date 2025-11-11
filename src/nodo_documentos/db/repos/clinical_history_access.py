from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nodo_documentos.db.models import ClinicalHistoryAccessLog


class ClinicalHistoryAccessRepository:
    """Data access layer for clinical history access logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_access(
        self,
        *,
        health_user_ci: str,
        health_worker_ci: str,
        clinic_name: str,
        viewed: bool,
        decision_reason: str | None,
    ) -> ClinicalHistoryAccessLog:
        """Insert an entry representing a history access attempt."""

        entry = ClinicalHistoryAccessLog(
            health_user_ci=health_user_ci,
            health_worker_ci=health_worker_ci,
            clinic_name=clinic_name,
            viewed=viewed,
            decision_reason=decision_reason,
        )

        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def list_by_health_user(
        self, health_user_ci: str
    ) -> list[ClinicalHistoryAccessLog]:
        """Return log entries for a patient ordered by most recent first."""

        stmt = (
            select(ClinicalHistoryAccessLog)
            .where(ClinicalHistoryAccessLog.health_user_ci == health_user_ci)
            .order_by(
                ClinicalHistoryAccessLog.requested_at.desc(),
                ClinicalHistoryAccessLog.id.desc(),
            )
        )
        result = await self._session.scalars(stmt)
        return list[ClinicalHistoryAccessLog](result.all())

    async def list_by_health_worker(
        self,
        health_worker_ci: str,
        health_user_ci: str | None = None,
    ) -> list[ClinicalHistoryAccessLog]:
        """Return log entries for a health worker ordered by most recent first."""

        stmt = select(ClinicalHistoryAccessLog).where(
            ClinicalHistoryAccessLog.health_worker_ci == health_worker_ci
        )

        if health_user_ci is not None:
            stmt = stmt.where(ClinicalHistoryAccessLog.health_user_ci == health_user_ci)

        stmt = stmt.order_by(
            ClinicalHistoryAccessLog.requested_at.desc(),
            ClinicalHistoryAccessLog.id.desc(),
        )

        result = await self._session.scalars(stmt)
        return list[ClinicalHistoryAccessLog](result.all())
