"""
Verifier access for the orchestrator. If VERIFIER_URL is set, checks run in the separate verifier
service over HTTP, which recomputes ground truth itself. If that service is configured but
unreachable, verification FAILS CLOSED (status FLAGGED_MISMATCH) rather than silently falling back
to the in-process check. If VERIFIER_URL is unset, the in-process VerifierAgent is used.
"""

import os
from datetime import datetime, timezone
from typing import Dict
import httpx
from engine.models import ProfileAssessment, ScenarioInput, VerificationReport, VerificationCheckItem
from .verifier_agent import VerifierAgent


def _unreachable(reason: str) -> VerificationReport:
    item = VerificationCheckItem(
        metric_name="Verifier service reachable",
        claimed_value_in_brief="n/a",
        engine_calculated_value="n/a",
        matched=False,
        discrepancy_note=f"Verifier service unavailable ({reason}); output blocked rather than shown unverified.",
    )
    return VerificationReport(
        status="FLAGGED_MISMATCH", total_checks=1, passed_checks=0, failed_checks=1, checks=[item],
        signature="UNVERIFIED:verifier_unreachable",
        verification_timestamp=datetime.now(timezone.utc).isoformat(),
    )


class VerifierClient:
    def __init__(self, timeout_s: float = 5.0):
        self._local = VerifierAgent()
        self._timeout = timeout_s

    @property
    def url(self) -> str:
        return os.getenv("VERIFIER_URL", "").rstrip("/")

    @property
    def mode(self) -> str:
        return "remote" if self.url else "in_process"

    def _headers(self) -> dict:
        """With VERIFIER_AUTH=google, send a Google-signed ID token (audience = verifier URL) so a private
        Cloud Run verifier accepts the call. Needs google-auth and a runtime service account."""
        if os.getenv("VERIFIER_AUTH", "").lower() != "google":
            return {}
        import google.auth.transport.requests
        import google.oauth2.id_token
        token = google.oauth2.id_token.fetch_id_token(google.auth.transport.requests.Request(), self.url)
        return {"Authorization": f"Bearer {token}"}

    def _post(self, path: str, payload: dict) -> VerificationReport:
        try:
            r = httpx.post(f"{self.url}{path}", json=payload, timeout=self._timeout, headers=self._headers())
            r.raise_for_status()
            return VerificationReport(**r.json())
        except Exception as e:
            return _unreachable(type(e).__name__)

    def verify_briefs(self, scenario: ScenarioInput, operator_brief: str, community_brief: str,
                      assessments: Dict[str, ProfileAssessment]) -> VerificationReport:
        if self.url:
            return self._post("/verify/briefs", {
                "scenario": scenario.model_dump(mode="json"),
                "operator_brief": operator_brief, "community_brief": community_brief})
        return self._local.verify_briefs(operator_brief, community_brief, assessments)

    def verify_text(self, scenario: ScenarioInput, text: str,
                    assessments: Dict[str, ProfileAssessment]) -> VerificationReport:
        if self.url:
            return self._post("/verify/text", {"scenario": scenario.model_dump(mode="json"), "text": text})
        return self._local.verify_text(text, assessments)
