import httpx
from loguru import logger

from nodo_documentos.api.schemas import AuthorizationDecision
from nodo_documentos.services.settings import services_settings


class AuthorizationService:
    """Integrates with HCEN to determine if a worker may view a clinical history."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
    ) -> None:
        self._base_url = (base_url or services_settings.hcen_api_base_url).rstrip("/")

    async def can_view_clinical_history(
        self,
        *,
        health_user_ci: str,
        health_worker_ci: str,
        clinic_id: str,
    ) -> AuthorizationDecision:
        payload = {
            "healthUserId": health_user_ci,
            "healthWorkerId": health_worker_ci,
            "clinicId": clinic_id,
        }
        url = f"{self._base_url}/authorization/check"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=5)

            except httpx.HTTPError as exc:  # pragma: no cover - network failure path
                logger.error(
                    "Authorization request to HCEN failed: {}",
                    exc,
                )
                return AuthorizationDecision(allowed=False, reason="hcen-unreachable")

        if response.status_code == 200:
            reason = response.json().get("decisionSource") if response.content else None
            return AuthorizationDecision(allowed=True, reason=reason)

        if response.status_code == 403:
            logger.info(
                "HCEN denied access for worker {} to patient {} at clinic {}",
                health_worker_ci,
                health_user_ci,
                clinic_id,
            )
            reason = response.json().get("decisionSource") if response.content else None
            return AuthorizationDecision(allowed=False, reason=reason)

        logger.error(
            "Unexpected status {} from HCEN authorization endpoint",
            response.status_code,
        )
        return AuthorizationDecision(allowed=False, reason="unexpected-status")
