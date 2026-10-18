"""
Independent Verifier Agent for AquaCarbon DC — Commons Edition (v2).
Acts as an independent trust boundary: every unit-tagged number in a generated text must
trace back to a deterministic engine value, and every headline engine value the briefs are
required to cite must actually appear.

Two complementary checks:
1. Presence: PUE, direct water, Scope 2 carbon and operating cost for each profile must be
   cited exactly (to the printed precision).
2. Claims: every unit-tagged number found in the text (PUE, ML, MWh, INR Cr, tCO2e, % of
   substation, % of water headroom) must match an engine value or a simple difference of two
   engine values (for example a power penalty). Numbers that match nothing are flagged,
   which catches fabricated additions as well as altered values.

Limit: only numbers that carry one of the recognised units are inspected. Free-form claims
without those units are not checked.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from itertools import combinations
from typing import Dict, List, Tuple
from engine.models import ProfileAssessment, VerificationReport, VerificationCheckItem

_NUM = r'(?<![0-9.])([0-9]+(?:\.[0-9]+)?)'

_CLAIM_PATTERNS: List[Tuple[str, str]] = [
    ('pue', rf'pue\s*(?:of|is|to|at|reaches|=|:)?\s*{_NUM}'),
    ('pue', rf'{_NUM}\s*pue'),
    ('water_ml', rf'{_NUM}\s*(?:million liters|megaliters|ml\b)'),
    ('energy_mwh', rf'{_NUM}\s*mwh'),
    ('cost_cr', rf'(?:₹|inr)\s*{_NUM}\s*(?:cr\b|crore)'),
    ('carbon_t', rf'{_NUM}\s*(?:tonnes|tco2)'),
    ('substation_pct', rf'{_NUM}\s*%\s*of\s*(?:the\s*)?(?:local\s*)?(?:[0-9/]+kv\s*)?(?:electrical\s*)?(?:substation|grid|feeder)'),
    ('headroom_pct', rf'{_NUM}\s*%\s*of\s*(?:the\s*)?(?:local\s*)?(?:(?:utility|industrial|municipal)\s*)*water\s*(?:headroom|buffer)'),
]


def _normalize(text: str) -> str:
    """Lowercase, drop markdown emphasis and thousands separators so numbers compare cleanly."""
    t = text.lower().replace('*', '')
    return re.sub(r'(?<=\d),(?=\d{3})', '', t)


def _decimals(num_str: str) -> int:
    return len(num_str.split('.')[1]) if '.' in num_str else 0


def _contains_number(normalized_text: str, num_str: str) -> bool:
    """True if num_str appears as a whole number (not as part of a longer one)."""
    return re.search(rf'(?<![0-9.]){re.escape(num_str)}(?![0-9])', normalized_text) is not None


def extract_claims(text: str) -> List[Tuple[str, str]]:
    """Returns de-duplicated (label, number-string) pairs for every unit-tagged number."""
    norm = _normalize(text)
    seen = set()
    claims: List[Tuple[str, str]] = []
    for label, pat in _CLAIM_PATTERNS:
        for m in re.finditer(pat, norm):
            key = (label, m.group(1))
            if key not in seen:
                seen.add(key)
                claims.append(key)
    return claims


def _allowed_values(assessments: Dict[str, ProfileAssessment]) -> Dict[str, List[float]]:
    fl = [a.facility_ledger for a in assessments.values()]
    cl = [a.community_ledger for a in assessments.values()]

    def with_diffs(vals: List[float]) -> List[float]:
        return list(vals) + [abs(a - b) for a, b in combinations(vals, 2)]

    def present(vals):
        return [v for v in vals if v is not None]

    return {
        'pue': [f.pue for f in fl],
        'water_ml': with_diffs([f.direct_water_consumption_ml for f in fl]),
        'energy_mwh': (
            with_diffs([f.total_facility_energy_mwh for f in fl])
            + [f.cooling_energy_mwh for f in fl]
            + [f.annual_it_energy_mwh for f in fl]
        ),
        'cost_cr': (
            with_diffs([f.annual_operating_cost_inr_crores for f in fl])
            + [f.electricity_cost_inr_crores for f in fl]
            + [f.water_cost_inr_crores for f in fl]
        ),
        'carbon_t': with_diffs([f.scope2_carbon_tonnes for f in fl]),
        'substation_pct': present([c.substation_peak_demand_share_pct.value for c in cl]),
        'headroom_pct': present([c.water_headroom_share_pct.value for c in cl]),
    }


def _matches(claimed: str, candidates: List[float]) -> bool:
    d = _decimals(claimed)
    tol = 0.5 * 10 ** (-d) + 1e-9
    value = float(claimed)
    return any(abs(value - c) <= tol for c in candidates)


def _build_report(checks: List[VerificationCheckItem]) -> VerificationReport:
    total = len(checks)
    passed = sum(1 for c in checks if c.matched)
    failed = total - passed
    status = "PASSED" if failed == 0 else "FLAGGED_MISMATCH"
    payload = json.dumps(
        [[c.metric_name, c.claimed_value_in_brief, c.engine_calculated_value, c.matched] for c in checks],
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    prefix = "VERIFIED_AUDIT_SHA256" if status == "PASSED" else "FLAGGED_AUDIT_SHA256"
    return VerificationReport(
        status=status,
        total_checks=total,
        passed_checks=passed,
        failed_checks=failed,
        checks=checks,
        signature=f"{prefix}:{digest}",
        verification_timestamp=datetime.now(timezone.utc).isoformat(),
    )


class VerifierAgent:
    """
    Independent verification service executing Section 8 fidelity checks.
    Deterministic: the signature is a SHA-256 over the check results, so identical inputs
    give an identical signature.
    """

    def _claim_checks(self, text: str, assessments: Dict[str, ProfileAssessment]) -> List[VerificationCheckItem]:
        allowed = _allowed_values(assessments)
        checks: List[VerificationCheckItem] = []
        for label, num in extract_claims(text):
            candidates = allowed.get(label, [])
            ok = _matches(num, candidates)
            nearest = min(candidates, key=lambda c: abs(c - float(num))) if candidates else None
            checks.append(VerificationCheckItem(
                metric_name=f"Claim check: {label}",
                claimed_value_in_brief=num,
                engine_calculated_value=(f"{nearest:.{_decimals(num)}f}" if nearest is not None else "n/a"),
                matched=ok,
                discrepancy_note=None if ok else f"{label} value {num} matches no engine output (nearest: {nearest})",
            ))
        return checks

    def verify_text(self, text: str, assessments: Dict[str, ProfileAssessment]) -> VerificationReport:
        """Claims-only check for free-form text such as an investigator answer."""
        return _build_report(self._claim_checks(text, assessments))

    def verify_briefs(
        self,
        operator_brief: str,
        community_brief: str,
        assessments: Dict[str, ProfileAssessment]
    ) -> VerificationReport:
        combined = operator_brief + "\n\n" + community_brief
        norm = _normalize(combined)
        checks: List[VerificationCheckItem] = []

        for assessment in assessments.values():
            fl = assessment.facility_ledger
            prefix = assessment.cooling_type.value.upper()

            required = [
                (f"{prefix} PUE", f"{fl.pue:.2f}", f"{fl.pue:.2f}"),
                (f"{prefix} Annual Direct Water (ML)", f"{fl.direct_water_consumption_ml:.1f}", f"{fl.direct_water_consumption_ml:.1f} ML"),
                (f"{prefix} Scope 2 Carbon (tCO2e)", f"{fl.scope2_carbon_tonnes:.0f}", f"{fl.scope2_carbon_tonnes:,.0f} tCO2e"),
                (f"{prefix} Operating Cost (INR Cr)", f"{fl.annual_operating_cost_inr_crores:.2f}", f"{fl.annual_operating_cost_inr_crores:.2f} Cr"),
            ]
            for name, needle, shown in required:
                found = _contains_number(norm, needle)
                checks.append(VerificationCheckItem(
                    metric_name=name,
                    claimed_value_in_brief=shown if found else "Not found or altered",
                    engine_calculated_value=shown,
                    matched=found,
                    discrepancy_note=None if found else f"Engine value {shown} is absent or altered in the brief text",
                ))

        checks.extend(self._claim_checks(combined, assessments))
        return _build_report(checks)
