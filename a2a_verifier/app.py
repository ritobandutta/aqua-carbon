"""
Permit-review verifier as an A2A agent. Run separately:  uvicorn a2a_verifier.app:app --port 8300

Independence (a real trust boundary, which is why this is A2A and not a function call): this process imports
only the engine and the verification code. It has no model client and never sees the reviewer's prompt or
reasoning. It receives the scenario, the claims and the review text, and recomputes the engine output itself.
"""

import json
import os
import warnings
from typing import AsyncGenerator

warnings.filterwarnings("ignore")

from google.adk.agents import BaseAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.events import Event
from google.genai import types

from review.models import VerifyReviewRequest
from review.verification import verify_review


class ReviewVerifierAgent(BaseAgent):
    """Takes a JSON VerifyReviewRequest as the user message and answers with a JSON VerificationReport."""

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        text = ""
        if ctx.user_content and ctx.user_content.parts:
            text = "\n".join(p.text for p in ctx.user_content.parts if getattr(p, "text", None))
        try:
            report = verify_review(VerifyReviewRequest.model_validate_json(text))
            payload = report.model_dump_json()
        except Exception as e:  # malformed request: answer with a failed report, never a crash
            payload = json.dumps({
                "status": "FLAGGED_MISMATCH", "total_checks": 1, "passed_checks": 0, "failed_checks": 1,
                "checks": [{"metric_name": "Request valid", "claimed_value_in_brief": "malformed",
                            "engine_calculated_value": "VerifyReviewRequest", "matched": False,
                            "discrepancy_note": f"{type(e).__name__}: {str(e)[:200]}"}],
                "signature": "UNVERIFIED:malformed_request", "verification_timestamp": "",
            })
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="model", parts=[types.Part(text=payload)]))


def build_app(host: str = "127.0.0.1", port: int = 8300, protocol: str = "http"):
    """The agent card advertises host:port, and clients reject a card whose URL is not the origin it was
    fetched from. So host, port and protocol must be the address clients actually use (set A2A_PUBLIC_*)."""
    agent = ReviewVerifierAgent(
        name="aquacarbon_review_verifier",
        description=("Independently verifies a permit review: that each claimed figure appears in the applicant's text, "
                     "that every verdict matches the deterministic engine, and that every number in the review traces to the engine."),
    )
    return to_a2a(agent, host=host, port=port, protocol=protocol)


app = build_app(
    os.getenv("A2A_PUBLIC_HOST", "127.0.0.1"),
    int(os.getenv("A2A_PUBLIC_PORT", "8300")),
    os.getenv("A2A_PUBLIC_PROTOCOL", "http"),
)
