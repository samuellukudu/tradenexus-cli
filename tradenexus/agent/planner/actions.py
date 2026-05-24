"""
tradenexus/agent/planner/actions.py

Phase 5 — Next best action: recommends next action for a given lead using AI.
Port of server/agent/planner/nextBestAction.ts
"""

from __future__ import annotations
import time

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead
from tradenexus.agent.types import AgentRecommendation
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


VALID_TYPES = {"VERIFY", "ENRICH", "DRAFT_OUTREACH", "PRIORITIZE", "REJECT", "USER_REVIEW", "EXPORT"}
VALID_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}


def recommend_next_actions(lead: Lead) -> list[AgentRecommendation]:
    """Recommend 2-4 next best actions for a lead based on its current state."""
    now = time.time()

    has_verification = bool(lead.verification)
    has_score = bool(lead.score_breakdown)
    has_social = bool(lead.social_discovery)
    has_evidence = bool(lead.evidence)
    has_contact = bool(lead.contact_email or lead.phone_number)

    verification_status = "UNVERIFIED"
    if isinstance(lead.verification, dict):
        verification_status = lead.verification.get("status", "UNVERIFIED")

    overall_score = 0
    if isinstance(lead.score_breakdown, dict):
        overall_score = lead.score_breakdown.get("overall", 0)

    prompt = f"""
You are a Sales Strategy Advisor. Based on the lead's current state, recommend the next best actions.

LEAD:
- Company: {lead.company_name}
- Region: {lead.region}
- Status: {lead.status.value}
- Confidence: {lead.confidence_score}/100
- Has Verification: {has_verification} ({verification_status})
- Has Score: {has_score} (overall: {overall_score}/100)
- Has Social Profiles: {has_social}
- Has Evidence: {has_evidence}
- Has Contact Info: {has_contact}
- Website: {lead.website or 'None'}

Recommend 2-4 next actions. Each action must have:
- type: One of VERIFY, ENRICH, DRAFT_OUTREACH, PRIORITIZE, REJECT, USER_REVIEW, EXTRACT
- priority: HIGH, MEDIUM, or LOW
- title: Short action title (max 8 words)
- reason: Why this action is recommended (1 sentence)

Rules:
- If not verified, VERIFY should be HIGH priority
- If scored >= 60 and verified but no outreach, DRAFT_OUTREACH should be HIGH
- If scored < 40, consider REJECT with MEDIUM priority
- Always include at least one actionable item

Return ONLY a JSON array. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
            ),
        )

        if not response.text:
            return _fallback_recommendations(lead, now)

        parsed = extract_json_from_text(response.text)
        if not parsed or not isinstance(parsed, list):
            return _fallback_recommendations(lead, now)

        recs = []
        for i, item in enumerate(parsed[:4]):
            recs.append(
                AgentRecommendation(
                    id=f"rec-{lead.id}-{int(now)}-{i}",
                    type=item.get("type") if item.get("type") in VALID_TYPES else "USER_REVIEW",
                    priority=item.get("priority") if item.get("priority") in VALID_PRIORITIES else "MEDIUM",
                    title=str(item.get("title", "Review this lead")),
                    reason=str(item.get("reason", "No reason provided.")),
                    created_at=now,
                )
            )
        return recs

    except Exception as e:
        print(f"[NextBestAction] Error for {lead.company_name}: {e}")
        return _fallback_recommendations(lead, now)


def _fallback_recommendations(lead: Lead, now: float) -> list[AgentRecommendation]:
    recs: list[AgentRecommendation] = []
    idx = 0

    if not lead.verification:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="VERIFY", priority="HIGH",
                title="Verify lead details",
                reason="Verification has not been completed yet.",
                created_at=now,
            )
        )
        idx += 1

    if not lead.score_breakdown:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="USER_REVIEW", priority="MEDIUM",
                title="Score this lead",
                reason="Lead scoring helps prioritize outreach efforts.",
                created_at=now,
            )
        )
        idx += 1

    if not lead.social_discovery:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="ENRICH", priority="MEDIUM",
                title="Find social profiles",
                reason="Social profiles provide additional contact channels.",
                created_at=now,
            )
        )
        idx += 1

    if not recs:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="USER_REVIEW", priority="LOW",
                title="Review lead status",
                reason="All automated checks complete — manual review recommended.",
                created_at=now,
            )
        )

    return recs
