"""
tradenexus/agent/scoring/lead.py

Phase 4 — AI-powered lead scoring with 10-dimensional breakdown.
Port of server/agent/scoring/leadScoring.ts
"""

from __future__ import annotations
import time
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import LeadScoreBreakdown
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def _clamp_score(value) -> int:
    if isinstance(value, (int, float)):
        return max(0, min(100, round(value)))
    return 50


def score_lead(
    lead: Lead,
    product: Optional[ProductDetails] = None,
) -> LeadScoreBreakdown:
    """Score a lead across 10 dimensions using AI."""
    now = time.time()
    product_name = product.name if product else "the product"

    evidence_count = len(lead.evidence) if lead.evidence else 0
    social_count = len(lead.social_discovery) if lead.social_discovery else 0
    verification_status = lead.verification.get("status", "UNVERIFIED") if isinstance(lead.verification, dict) else "UNVERIFIED"

    prompt = f"""
You are a Lead Scoring Specialist. Score this lead across 10 dimensions based on available data.

LEAD: "{lead.company_name}"
REGION: {lead.region}
WEBSITE: {lead.website or 'None'}
CONFIDENCE: {lead.confidence_score}/100
EVIDENCE RECORDS: {evidence_count}
SOCIAL PROFILES: {social_count}
VERIFICATION STATUS: {verification_status}
EMPLOYEE COUNT: {lead.employee_count or 'Unknown'}
HAS CONTACT INFO: {'Yes' if (lead.contact_email or lead.phone_number) else 'No'}

PRODUCT: {product_name}

CONTEXT: {lead.summary or 'No summary available.'}

Score each dimension 0-100 (0 = worst, 100 = best):

1. locationFit — Is the lead in the right region?
2. productFit — Does this company need/could use {product_name}?
3. buyerTypeFit — Is this company the right buyer type?
4. companySizeFit — Is the company appropriately sized?
5. evidenceQuality — How good is the evidence?
6. socialActivity — How active is the company on social media?
7. contactability — Can we contact this company?
8. competitiveOpportunity — Is there a gap in the market? Are competitors weak?
9. freshness — How recently was this lead discovered?
10. overall — Weighted average, weighted toward productFit and evidenceQuality.

Also provide rationale: 2-3 sentences explaining the overall score.

Return ONLY a JSON object with numeric fields. No markdown wrapping.
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
            return LeadScoreBreakdown(rationale="Model returned empty response", updated_at=now)

        parsed = extract_json_from_text(response.text)
        if not parsed:
            return LeadScoreBreakdown(rationale="Could not parse model response", updated_at=now)

        return LeadScoreBreakdown(
            overall=_clamp_score(parsed.get("overall")),
            location_fit=_clamp_score(parsed.get("locationFit")),
            product_fit=_clamp_score(parsed.get("productFit")),
            buyer_type_fit=_clamp_score(parsed.get("buyerTypeFit")),
            company_size_fit=_clamp_score(parsed.get("companySizeFit")),
            evidence_quality=_clamp_score(parsed.get("evidenceQuality")),
            social_activity=_clamp_score(parsed.get("socialActivity")),
            contactability=_clamp_score(parsed.get("contactability")),
            competitive_opportunity=_clamp_score(parsed.get("competitiveOpportunity")),
            freshness=_clamp_score(parsed.get("freshness")),
            rationale=parsed.get("rationale", "Score generated from available data."),
            updated_at=now,
        )

    except Exception as e:
        print(f"[LeadScoring] Error for {lead.company_name}: {e}")
        return LeadScoreBreakdown(rationale=f"Scoring error: {e}", updated_at=now)
