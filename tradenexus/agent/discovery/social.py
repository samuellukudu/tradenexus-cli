"""
tradenexus/agent/discovery/social.py

Phase 2 — Social media discovery for known companies and region-based lead discovery.
Port of server/agent/discovery/socialDiscovery.ts
"""

from __future__ import annotations
import uuid
import time
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, GROUNDING_MODEL, build_thinking_config
from tradenexus.models import StrategicContext
from tradenexus.agent.types import SocialProfileEvidence
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


PLATFORMS = ["linkedin", "facebook", "instagram", "youtube", "tiktok", "x"]


# ---------------------------------------------------------------------------
# discover_social_for_company
# ---------------------------------------------------------------------------

def discover_social_for_company(
    company_name: str,
    region: str,
    website: Optional[str] = None,
    product_context: Optional[StrategicContext] = None,
) -> list[SocialProfileEvidence]:
    """Find official social media profiles for a target company."""
    now = time.time()

    product_hint = ""
    if product_context:
        product_hint = (
            f"Product context: {product_context.product_identity}. "
            f"Ideal buyer: {product_context.ideal_buyer}."
        )
    website_hint = f"Website: {website}" if website else ""

    prompt = f"""
You are a B2B Sales Intelligence Researcher. Your job is to find official social media profiles for a target company.

COMPANY: "{company_name}"
REGION: {region}
{website_hint}
{product_hint}

TASK: Search for this company's presence on these platforms: LinkedIn, Facebook, Instagram, YouTube, TikTok, X (Twitter).

For each platform where you find a profile, classify it:

PROFILE TYPES:
- "company" — Official company page or business profile
- "employee" — Individual employee or founder profile (not the company itself)
- "reseller" — A distributor/reseller page mentioning the company
- "community" — Fan page, group, or community
- "unknown" — Cannot determine

ACTIVITY LEVELS:
- "HIGH" — Recent posts (within last month), active engagement visible
- "MEDIUM" — Profile exists, some activity but not frequent
- "LOW" — Profile exists but appears inactive or very sparse
- "UNKNOWN" — Cannot assess activity from available data

CONFIDENCE (0.0 to 1.0):
- 0.9-1.0: Exact company name match, verified location, consistent branding
- 0.7-0.89: Strong name match, same industry/region
- 0.5-0.69: Partial name match or similar industry
- 0.3-0.49: Weak match, might be related
- 0.0-0.29: Very uncertain

Return a JSON object with a "profiles" array. Each profile object must have these keys:
- platform, url, handle, isOfficialLikely (boolean), profileType, activityLevel,
  activityEvidence, contactHints (array of strings), relevanceNotes, confidence (number 0-1)

IMPORTANT: Only include profiles you actually found. Do not fabricate.
Return ONLY the raw JSON object, no markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=GROUNDING_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(GROUNDING_MODEL),
                tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
            ),
        )

        if not response.text:
            return []

        parsed = extract_json_from_text(response.text)
        if not parsed or not isinstance(parsed.get("profiles"), list):
            return []

        return [
            SocialProfileEvidence(
                id=str(uuid.uuid4()),
                source_type=p.get("platform", "other"),
                url=p.get("url", ""),
                title=f"{company_name} - {p.get('platform', '')}",
                snippet=p.get("relevanceNotes"),
                confidence=float(p.get("confidence", 0.5)),
                found_at=now,
                found_by="socialDiscovery",
                validation_status="UNVERIFIED",
                platform=p.get("platform", "other"),
                handle=p.get("handle"),
                is_official_likely=bool(p.get("isOfficialLikely")),
                profile_type=p.get("profileType", "unknown"),
                activity_level=p.get("activityLevel", "UNKNOWN"),
                activity_evidence=p.get("activityEvidence"),
                contact_hints=p.get("contactHints") if isinstance(p.get("contactHints"), list) else [],
                relevance_notes=p.get("relevanceNotes"),
            )
            for p in parsed["profiles"]
        ]

    except Exception as e:
        print(f"[SocialDiscovery] Error for {company_name}: {e}")
        return []


# ---------------------------------------------------------------------------
# discover_leads_from_social
# ---------------------------------------------------------------------------

def discover_leads_from_social(
    product_name: str,
    region: str,
    product_context: Optional[StrategicContext] = None,
) -> list[SocialProfileEvidence]:
    """Find potential buyer companies in a target region via social media."""
    now = time.time()

    product_hint = ""
    if product_context:
        product_hint = (
            f"Product: {product_context.product_identity}. "
            f"Ideal buyer: {product_context.ideal_buyer}. "
            f"Value proposition: {product_context.value_proposition}."
        )
    else:
        product_hint = f"Product: {product_name}."

    exclude_hint = ""
    if product_context and product_context.exclusions:
        exclude_hint = f"EXCLUDE these company types: {product_context.exclusions}."

    prompt = f"""
You are a B2B Sales Intelligence Researcher. Find potential buyer or distributor companies in a target region by searching for their social media presence.

PRODUCT TO SELL: {product_name}
TARGET REGION: {region}
{product_hint}
{exclude_hint}

TASK: Search social media platforms (LinkedIn, Facebook, Instagram, YouTube, TikTok, X) for companies in {region} that could be potential buyers, distributors, or importers of {product_name}.

For each company you find, provide their social profile details. Focus on:
1. Companies that match the ideal buyer profile
2. Companies with active social media presence (indicates they're real businesses)
3. Companies in the specified region

PROFILE TYPES: "company", "employee", "founder", "reseller", "community", "unknown"
ACTIVITY LEVELS: "HIGH", "MEDIUM", "LOW", "UNKNOWN"
CONFIDENCE: 0.0 to 1.0

Return a JSON object with a "profiles" array. Each profile: companyName, platform, url, handle,
isOfficialLikely, profileType, activityLevel, activityEvidence, contactHints, relevanceNotes,
confidence, employeeCount, website.

AIM FOR 8-15 RESULTS. Focus on quality.
Return ONLY the raw JSON object, no markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=GROUNDING_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(GROUNDING_MODEL),
                tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
            ),
        )

        if not response.text:
            return []

        parsed = extract_json_from_text(response.text)
        if not parsed or not isinstance(parsed.get("profiles"), list):
            return []

        return [
            SocialProfileEvidence(
                id=str(uuid.uuid4()),
                source_type=p.get("platform", "other"),
                url=p.get("url", ""),
                title=p.get("companyName", f"{product_name} lead"),
                snippet=p.get("relevanceNotes"),
                confidence=float(p.get("confidence", 0.5)),
                found_at=now,
                found_by="socialDiscovery",
                validation_status="UNVERIFIED",
                platform=p.get("platform", "other"),
                handle=p.get("handle"),
                is_official_likely=bool(p.get("isOfficialLikely")),
                profile_type=p.get("profileType", "unknown"),
                activity_level=p.get("activityLevel", "UNKNOWN"),
                activity_evidence=p.get("activityEvidence"),
                contact_hints=p.get("contactHints") if isinstance(p.get("contactHints"), list) else [],
                relevance_notes=p.get("relevanceNotes"),
                extracted_fields={
                    "companyName": p.get("companyName", ""),
                    "website": p.get("website", ""),
                    "region": region,
                    "employeeCount": p.get("employeeCount", ""),
                },
            )
            for p in parsed["profiles"]
        ]

    except Exception as e:
        print(f"[SocialDiscovery] Error discovering leads for {product_name} in {region}: {e}")
        return []
