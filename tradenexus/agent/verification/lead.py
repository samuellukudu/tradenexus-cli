"""
tradenexus/agent/verification/lead.py

Phase 4 — Multi-check lead verification that cross-references evidence.
Port of server/agent/verification/leadVerification.ts
"""

from __future__ import annotations
import uuid
import time
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import LeadVerification, VerificationCheck
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def verify_lead(
    lead: Lead,
    product: Optional[ProductDetails] = None,
) -> LeadVerification:
    """Run 6 verification checks (LOCATION, WEBSITE, PRODUCT_FIT, SOCIAL_OWNERSHIP, CONTACT, DUPLICATE)."""
    now = time.time()

    product_name = product.name if product else "the product"

    # Build evidence list string from lead.evidence (list of dicts or DiscoveryEvidence objects)
    evidence_list = ""
    if lead.evidence:
        evidence_items = lead.evidence if isinstance(lead.evidence, list) else []
        if evidence_items:
            lines = []
            for e in evidence_items:
                st = e.get("source_type", e.source_type if hasattr(e, "source_type") else "?")
                url = e.get("url", e.url if hasattr(e, "url") else "?")
                conf = e.get("confidence", e.confidence if hasattr(e, "confidence") else 0)
                lines.append(f"- {st}: {url} (confidence: {conf})")
            evidence_list = "\n".join(lines)
    if not evidence_list:
        evidence_list = "No evidence available."

    # Build social profiles string
    social_profiles_str = ""
    if lead.social_discovery:
        sp_list = lead.social_discovery if isinstance(lead.social_discovery, list) else []
        if sp_list:
            lines = []
            for s in sp_list:
                plat = s.get("platform", s.platform if hasattr(s, "platform") else "?")
                url = s.get("url", s.url if hasattr(s, "url") else "?")
                official = s.get("isOfficialLikely", s.is_official_likely if hasattr(s, "is_official_likely") else False)
                lines.append(f"- {plat}: {url} (official: {official})")
            social_profiles_str = "\n".join(lines)
    if not social_profiles_str:
        social_profiles_str = "No social profiles discovered."

    prompt = f"""
You are a Lead Verification Specialist. Verify the legitimacy of a sales lead using available evidence.

LEAD: "{lead.company_name}"
REGION: {lead.region}
WEBSITE: {lead.website or 'Unknown'}
ADDRESS: {lead.address or 'Unknown'}
CONFIDENCE SCORE: {lead.confidence_score}/100
GOOGLE MAPS URL: {lead.google_maps_url or 'Not available'}

PRODUCT WE ARE SELLING: {product_name}

EVIDENCE RECORDS:
{evidence_list}

SOCIAL PROFILES:
{social_profiles_str}

TASK: Run these verification checks and return a JSON object:

1. LOCATION — Does the company physically exist in {lead.region}? Check Google Maps data, address validity.
2. WEBSITE — Is the website active and relevant to their claimed business?
3. PRODUCT_FIT — Does this company potentially buy, distribute, or use {product_name}?
4. SOCIAL_OWNERSHIP — Do the social profiles genuinely belong to this company?
5. CONTACT — Is there usable contact information available?
6. DUPLICATE — Any sign this is a duplicate of another known lead? (usually PASS unless evidence suggests duplication)

For EACH check, return: type, status (PASS|FAIL|WARNING|UNKNOWN), confidence (0-1), notes, evidenceIds (empty array).

OVERALL:
- status: "VERIFIED" (all critical pass), "PARTIAL" (most pass but some warnings), "FAILED" (critical fail), or "UNVERIFIED" (insufficient data)
- confidence: 0-1

Return ONLY a JSON object with "checks" array and "status"/"confidence" fields. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
                tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
            ),
        )

        if not response.text:
            return LeadVerification(
                status="UNVERIFIED",
                confidence=0,
                checks=[
                    VerificationCheck(
                        id=str(uuid.uuid4()),
                        type="LOCATION",
                        status="UNKNOWN",
                        confidence=0,
                        notes="Verification failed: model returned empty response.",
                    )
                ],
                updated_at=now,
            )

        parsed = extract_json_from_text(response.text)
        if not parsed:
            return LeadVerification(
                status="UNVERIFIED",
                confidence=0,
                checks=[
                    VerificationCheck(
                        id=str(uuid.uuid4()),
                        type="LOCATION",
                        status="UNKNOWN",
                        confidence=0,
                        notes="Verification failed: could not parse model response.",
                    )
                ],
                updated_at=now,
            )

        parsed_checks = []
        for c in (parsed.get("checks") or []):
            parsed_checks.append(
                VerificationCheck(
                    id=str(uuid.uuid4()),
                    type=c.get("type", "LOCATION"),
                    status=c.get("status", "UNKNOWN"),
                    confidence=float(c.get("confidence", 0.5)),
                    notes=c.get("notes", ""),
                    evidence_ids=c.get("evidenceIds") if isinstance(c.get("evidenceIds"), list) else [],
                )
            )

        return LeadVerification(
            status=parsed.get("status", "UNVERIFIED"),
            confidence=float(parsed.get("confidence", 0)),
            checks=parsed_checks,
            updated_at=now,
        )

    except Exception as e:
        print(f"[LeadVerification] Error for {lead.company_name}: {e}")
        return LeadVerification(
            status="UNVERIFIED",
            confidence=0,
            checks=[
                VerificationCheck(
                    id=str(uuid.uuid4()),
                    type="LOCATION",
                    status="UNKNOWN",
                    confidence=0,
                    notes=f"Verification error: {e}",
                )
            ],
            updated_at=now,
        )
