"""
tradenexus/core/leads.py

Lead discovery and verification.
Port of searchForLeads(), verifyLead(), and internal helpers.
"""

from __future__ import annotations
import asyncio
import json
import uuid
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import (
    Competitor, InteractionLog, Lead, LeadStatus,
    MatchDetails, ProductDetails, SocialProfile, StrategicContext,
)
from tradenexus.utils import (
    extract_json_from_text,
    extract_grounding_urls,
    normalize_confidence,
)


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


# ---------------------------------------------------------------------------
# verify_lead
# ---------------------------------------------------------------------------

def verify_lead(lead: Lead, product: ProductDetails) -> dict:
    """Port of verifyLead(). Returns partial Lead update dict."""
    client = _client()
    prompt = (
        f'You are a Lead Verification Specialist.\n'
        f'TASK: Verify the legitimacy and relevance of "{lead.company_name}" in "{lead.region}".\n'
        f'PRODUCT CONTEXT: We are selling "{product.name}".\n\n'
        f'CURRENT DATA:\n'
        f'- Address: {lead.address or "Unknown"}\n'
        f'- Website: {lead.website or "Unknown"}\n\n'
        "VERIFICATION STEPS:\n"
        "1. Search Google Maps for the company name in the region.\n"
        "2. Search Google for the company + product category.\n"
        "3. Check if the website is active and relevant.\n\n"
        "Return ONLY raw JSON (no markdown) with keys: "
        "verificationStatus (VERIFIED|FAILED|UNVERIFIED), verificationNotes (string), "
        "confidenceScore (number 0-100)."
    )

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents={"parts": [{"text": prompt}]},
        config=gtypes.GenerateContentConfig(
            **_thinking(DEFAULT_MODEL),
            tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
        ),
    )

    if not response.text:
        raise RuntimeError("Empty response from model during lead verification")

    parsed = extract_json_from_text(response.text) or {}
    parsed["_sources"] = extract_grounding_urls(response)
    return parsed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _identify_strategic_hubs(product: ProductDetails) -> list[str]:
    """Port of identifyStrategicHubs(). Returns up to 12 hub names."""
    client = _client()
    prompt = (
        f'I am analyzing the export market for "{product.name}" in "{product.target_region}".\n\n'
        "Task: Identify the top 12 most important industrial hubs, cities, or trade zones "
        f'in "{product.target_region}" specifically relevant to this product category.\n\n'
        "Rules:\n"
        "1. If target_region is a Continent → list top 12 COUNTRIES.\n"
        "2. If target_region is a Country → list top 12 CITIES or Industrial Regions.\n"
        "3. If target_region is All/Global → list top 12 Global Trade Hub Countries.\n\n"
        "Return ONLY a JSON array of strings."
    )

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents={"parts": [{"text": prompt}]},
        config=gtypes.GenerateContentConfig(
            **_thinking(DEFAULT_MODEL),
            response_mime_type="application/json",
            response_schema={"type": "array", "items": {"type": "string"}},
        ),
    )

    if not response.text:
        return ["Major Cities", "Industrial Zones", "Port Cities", "Capital Region"]
    cities = json.loads(response.text)
    return cities if isinstance(cities, list) and cities else ["Major Cities", "Industrial Zones"]


def _execute_lead_batch(
    product: ProductDetails,
    vector_name: str,
    vector_prompt: str,
    target_count: int,
    context: Optional[StrategicContext] = None,
) -> list[dict]:
    """Port of executeLeadBatch(). Single AI call for one batch of leads."""
    client = _client()
    request_count = target_count + 2

    memory_block = ""
    if context:
        memory_block = (
            f"\nSTRATEGIC MEMORY ACTIVATED:\n"
            f"- SEARCH IDENTITY: {context.product_identity}\n"
            f"- IDEAL TARGET: {context.ideal_buyer}\n"
            f"- NEGATIVE MATCH (EXCLUDE): {context.exclusions}\n"
            f"- VALUE HOOK: {context.value_proposition}\n"
        )

    full_prompt = (
        f"You are a TERRITORY MANAGER for a Lead Sourcing Agency.\n"
        f'ASSIGNED TERRITORY: "{vector_name}"\n\n'
        f"PRODUCT: {product.name}\n"
        f"REGION: {product.target_region}\n"
        f"TARGET: Find AT LEAST {request_count} verified candidates in your territory.\n\n"
        f"LOCATION ENFORCEMENT (CRITICAL):\n"
        f"- Search specifically in {product.target_region}.\n"
        f"- EXCLUDE companies headquartered in {product.supplier_country or 'China'} "
        f"unless the target region IS {product.supplier_country or 'China'}.\n\n"
        f"INSTRUCTIONS:\n{vector_prompt}\n\n"
        f"{memory_block}\n"
        "STRICT VERIFICATION PROTOCOL:\n"
        "1. Find companies with a PHYSICAL PRESENCE in the region.\n"
        "2. For every lead, search for their Google Maps URL or Street Address.\n"
        "3. Discard any company not found on Maps.\n"
        "4. Populate googleMapsUrl and country fields.\n"
        "5. Identify 1-2 current suppliers they may be using + displacement strategy.\n\n"
        "Return ONLY raw JSON array (no markdown). Each object must have: "
        "companyName, website, reason, confidenceScore (number), sourceUrl, "
        "googleMapsUrl, country, socialProfiles (array of {platform, url}), "
        "employeeCount, revenue, contactEmail, phoneNumber, address, "
        "tradeVolume, manufacturingVolume, "
        "matchDetails ({industryFit, sizeFit, locationFit}), "
        "competitors (array of {name, strengths, weaknesses, displacementStrategy})."
    )

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents={"parts": [{"text": full_prompt}]},
        config=gtypes.GenerateContentConfig(
            **_thinking(DEFAULT_MODEL),
            tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
        ),
    )

    if not response.text:
        return []

    raw = extract_json_from_text(response.text)
    raw_leads = raw if isinstance(raw, list) else []
    grounding_urls = extract_grounding_urls(response)

    target_lower = (product.target_region or "").lower()
    verified: list[dict] = []
    for lead in raw_leads:
        maps_url = lead.get("googleMapsUrl", "")
        has_maps = any(
            kw in maps_url
            for kw in ["google.com/maps", "google.co", "goo.gl/maps", "maps.app.goo.gl", "maps.google"]
        )
        if not has_maps:
            continue
        country = (lead.get("country") or "").lower()
        if "australia" in target_lower and ("usa" in country or "united states" in country or "texas" in country):
            continue
        if "uae" in target_lower and ("india" in country or "mumbai" in country):
            continue
        lead["_sources"] = grounding_urls
        verified.append(lead)

    return verified


def _run_search_vector(
    product: ProductDetails,
    vector_name: str,
    vector_prompt: str,
    raw_count: int,
) -> list[Lead]:
    """Port of runSearchVector(). Splits into batches of 8 and maps to Lead objects."""
    MAX_PER_BATCH = 8
    batches: list[int] = []
    remaining = raw_count
    while remaining > 0:
        take = min(remaining, MAX_PER_BATCH)
        batches.append(take)
        remaining -= take

    all_raw: list[dict] = []
    for count in batches:
        results = _execute_lead_batch(
            product, vector_name, vector_prompt, count, product.strategic_context
        )
        all_raw.extend(results)

    leads: list[Lead] = []
    for raw in all_raw:
        md_raw = raw.get("matchDetails") or {}
        md = MatchDetails(
            industry_fit=md_raw.get("industryFit", ""),
            size_fit=md_raw.get("sizeFit", ""),
            location_fit=md_raw.get("locationFit", ""),
        )
        competitors = [
            Competitor(
                name=c.get("name", ""),
                strengths=c.get("strengths", ""),
                weaknesses=c.get("weaknesses", ""),
                displacement_strategy=c.get("displacementStrategy", ""),
            )
            for c in (raw.get("competitors") or [])
        ]
        social_profiles = [
            SocialProfile(platform=s.get("platform", ""), url=s.get("url", ""))
            for s in (raw.get("socialProfiles") or [])
        ]
        sources = raw.get("_sources") or []
        maps_url = raw.get("googleMapsUrl")
        country = raw.get("country", "Detected in Region")

        leads.append(
            Lead(
                id=str(uuid.uuid4()),
                company_name=raw.get("companyName", "Unknown"),
                website=raw.get("website") if str(raw.get("website", "")).lower() != "n/a" else None,
                region=product.target_region or "Unknown",
                status=LeadStatus.DISCOVERED,
                confidence_score=normalize_confidence(raw.get("confidenceScore")),
                match_details=md,
                summary=raw.get("reason"),
                social_profiles=social_profiles,
                employee_count=raw.get("employeeCount"),
                revenue=raw.get("revenue"),
                contact_email=raw.get("contactEmail"),
                phone_number=raw.get("phoneNumber"),
                address=raw.get("address"),
                source_url=raw.get("sourceUrl"),
                google_maps_url=maps_url,
                trade_volume=raw.get("tradeVolume"),
                manufacturing_volume=raw.get("manufacturingVolume"),
                search_vector=vector_name,
                sources=sources,
                competitors=competitors,
                logs=[
                    InteractionLog(
                        timestamp="now",
                        actor="SYSTEM",
                        message=(
                            f"Lead discovered via {vector_name}.\n"
                            f"Location Verified: {maps_url}\n"
                            f"HQ: {country}"
                            + (f"\nSearch Sources: {len(sources)} URLs" if sources else "")
                        ),
                    )
                ],
            )
        )
    return leads


# ---------------------------------------------------------------------------
# search_for_leads
# ---------------------------------------------------------------------------

def search_for_leads(product: ProductDetails) -> list[Lead]:
    """Port of searchForLeads(). Launches 4 geographic territory squads in parallel."""
    total = product.target_lead_count or 20
    per_vector = -(-total // 4)  # ceiling division

    hubs = _identify_strategic_hubs(product)
    chunk = max(1, len(hubs) // 4)
    a = hubs[0:chunk]
    b = hubs[chunk:chunk * 2]
    c = hubs[chunk * 2:chunk * 3]
    d = hubs[chunk * 3:]

    squad_a = ", ".join(a) if a else "Major Cities"
    squad_b = ", ".join(b) if b else "Secondary Cities"
    squad_c = ", ".join(c) if c else "Industrial Zones"
    squad_d = ", ".join(d) if d else "Developing Regions"

    def prompt(locs: str) -> str:
        return (
            f"YOUR MISSION: SATURATE THE FOLLOWING LOCATIONS: [ {locs} ].\n\n"
            f"EXECUTE MULTI-METHOD SEARCH IN THESE CITIES:\n"
            f"1. COMMERCIAL: Search for 'Wholesaler of {product.name} in [City Name]'.\n"
            f"2. MAPS: Search for 'Distributors near [City Name]' on Google Maps.\n"
            f"3. COMPETITOR: Find who stocks rival brands in these specific towns.\n"
            f"4. DIRECTORY: Check local chamber of commerce member lists.\n"
            f"Verify every address found."
        )

    async def _run_all() -> list[Lead]:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                None, _run_search_vector, product,
                f"Territory Scout: {sq[:30]}...", prompt(sq), per_vector
            )
            for sq in [squad_a, squad_b, squad_c, squad_d]
        ]
        results = await asyncio.gather(*tasks)
        combined: list[Lead] = []
        for r in results:
            combined.extend(r)
        return combined

    return asyncio.run(_run_all())
