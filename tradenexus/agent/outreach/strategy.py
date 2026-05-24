"""
tradenexus/agent/outreach/strategy.py

Phase 6 — Closing strategy: selects the best deal-closing approach for a lead.
Port of server/agent/outreach/closingStrategy.ts
"""

from __future__ import annotations
import time
import json
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import ClosingStrategy
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


VALID_STRATEGY_TYPES = {
    "DIRECT_VALUE_PITCH", "COMPETITIVE_DISPLACEMENT", "EDUCATIONAL_HOOK",
    "PROBLEM_SOLUTION", "PARTNERSHIP_APPROACH", "CASE_STUDY_APPROACH",
}

VALID_PLATFORMS = {
    "cold_email", "linkedin_connection", "linkedin_followup",
    "whatsapp_short", "tradeshow_intro", "distributor_pitch",
}


def generate_closing_strategy(
    lead: Lead,
    product: Optional[ProductDetails] = None,
) -> ClosingStrategy:
    """Select the best closing strategy for a lead based on evidence and profile."""
    now = time.time()
    product_name = product.name if product else "our product"

    evidence_summary = []
    for e in (lead.evidence or [])[:10]:
        if isinstance(e, dict):
            evidence_summary.append({
                "type": e.get("source_type", e.get("sourceType", "?")),
                "title": e.get("title", ""),
                "snippet": (e.get("snippet", "") or "")[:200],
                "confidence": e.get("confidence", 0),
            })

    social_summary = []
    for s in (lead.social_discovery or [])[:10]:
        if isinstance(s, dict):
            social_summary.append({
                "platform": s.get("platform", "?"),
                "activityLevel": s.get("activity_level", s.get("activityLevel", "?")),
                "isOfficial": s.get("is_official_likely", s.get("isOfficialLikely", False)),
                "relevance": (s.get("relevance_notes", s.get("relevanceNotes", "")) or "")[:150],
            })

    has_competitors = bool(lead.competitors)
    competitor_summary = []
    if has_competitors:
        for c in (lead.competitors or []):
            name = c.name if hasattr(c, 'name') else c.get('name', '?')
            weaknesses = (c.weaknesses if hasattr(c, 'weaknesses') else c.get('weaknesses', '')) or ''
            competitor_summary.append(f"{name}: weakness={weaknesses[:100]}")

    overall_score = 0
    if isinstance(lead.score_breakdown, dict):
        overall_score = lead.score_breakdown.get("overall", 0)

    verification_status = "UNVERIFIED"
    if isinstance(lead.verification, dict):
        verification_status = lead.verification.get("status", "UNVERIFIED")

    prompt = f"""
You are a B2B Sales Strategist specializing in international trade. Select the best closing strategy for this lead.

LEAD PROFILE:
- Company: {lead.company_name}
- Region: {lead.region}
- Lead Score: {overall_score}/100
- Verification: {verification_status}
- Has Contact Info: {'Yes' if (lead.contact_email or lead.phone_number) else 'No'}
- Has Social Presence: {'Yes' if social_summary else 'No'}

EVIDENCE GATHERED ({len(evidence_summary)} records):
{json.dumps(evidence_summary, indent=2)}

SOCIAL PROFILES ({len(social_summary)} profiles):
{json.dumps(social_summary, indent=2)}

{('COMPETITORS:\\n' + chr(10).join(competitor_summary)) if has_competitors else 'COMPETITORS: None identified'}

PRODUCT: {product_name}

Select ONE closing strategy from:
- DIRECT_VALUE_PITCH: Lead has clear need, strong evidence. Pitch value directly.
- COMPETITIVE_DISPLACEMENT: Competitors identified with known weaknesses.
- EDUCATIONAL_HOOK: Lead may not understand the product category. Educate first.
- PROBLEM_SOLUTION: Lead has specific pain point. Position as the solution.
- PARTNERSHIP_APPROACH: Strategic fit for long-term partnership.
- CASE_STUDY_APPROACH: Similar companies have succeeded. Lead with success story.

Return ONLY a JSON object with: type, rationale, keyTalkingPoints (3-5), evidenceToHighlight (2-4), recommendedPlatform, confidence (0-100).
No markdown wrapping.
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
            return _fallback_strategy(lead, now, "Model returned empty response")

        parsed = extract_json_from_text(response.text)
        if not parsed:
            return _fallback_strategy(lead, now, "Could not parse model response")

        return ClosingStrategy(
            type=parsed.get("type") if parsed.get("type") in VALID_STRATEGY_TYPES else "DIRECT_VALUE_PITCH",
            rationale=str(parsed.get("rationale", "Strategy selected based on lead profile analysis.")),
            key_talking_points=parsed.get("keyTalkingPoints") if isinstance(parsed.get("keyTalkingPoints"), list) else [],
            evidence_to_highlight=parsed.get("evidenceToHighlight") if isinstance(parsed.get("evidenceToHighlight"), list) else [],
            recommended_platform=parsed.get("recommendedPlatform") if parsed.get("recommendedPlatform") in VALID_PLATFORMS else "cold_email",
            confidence=max(0, min(100, round(float(parsed.get("confidence", 70))))),
            generated_at=now,
        )

    except Exception as e:
        print(f"[ClosingStrategy] Error for {lead.company_name}: {e}")
        return _fallback_strategy(lead, now, f"Strategy error: {e}")


def _fallback_strategy(lead: Lead, now: float, reason: str) -> ClosingStrategy:
    has_competitors = bool(lead.competitors)
    has_social = bool(lead.social_discovery)
    return ClosingStrategy(
        type="COMPETITIVE_DISPLACEMENT" if has_competitors else "DIRECT_VALUE_PITCH",
        rationale=f"Fallback strategy: {reason}.",
        key_talking_points=[
            "Our product quality and competitive pricing",
            "Reliable supply chain and on-time delivery",
            "Flexible order quantities and customization options",
        ],
        recommended_platform="linkedin_connection" if has_social else "cold_email",
        confidence=30,
        generated_at=now,
    )
