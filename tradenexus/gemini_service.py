"""
tradenexus/gemini_service.py

Python port of services/geminiService.ts from tradenexus-ai-sales-agent.
All public functions mirror their TypeScript counterparts exactly.
"""

from __future__ import annotations
import asyncio
import base64
import json
from pathlib import Path
from typing import Optional
import uuid

from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types as gtypes

from .config import get_api_key, DEFAULT_MODEL, GROUNDING_MODEL, build_thinking_config
from .models import (
    ChatMessage, Competitor, InteractionLog, Lead, LeadStatus,
    MatchDetails, MarketReport, MarketReportSource, MarketStats,
    ProductAsset, ProductDetails, RegionSuggestion, SocialProfile,
    StatPoint, StrategicContext,
)
from .utils import (
    extract_json_from_text,
    extract_grounding_sources,
    extract_grounding_urls,
    normalize_confidence,
)

FALLBACK_CONTEXT = StrategicContext()


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


# ---------------------------------------------------------------------------
# extract_search_strategy_from_assets
# ---------------------------------------------------------------------------

def extract_search_strategy_from_assets(product: ProductDetails) -> StrategicContext:
    """Port of extractSearchStrategyFromAssets(). Analyses product files → StrategicContext."""
    if not product.assets:
        return FALLBACK_CONTEXT

    client = _client()
    prompt = (
        "You are a Senior Technical Sales Engineer.\n"
        "I have uploaded product catalogues/spec sheets.\n\n"
        "TASK: Perform a deep analysis and extract a STRATEGIC MEMORY OBJECT.\n\n"
        "EXTRACT THE FOLLOWING INTO JSON:\n"
        "1. productIdentity: A concise 3-5 word name.\n"
        "2. technicalSpecs: Array of top 5 critical specs.\n"
        "3. certifications: Array of ALL compliance codes found (UL, CE, IEC, UN38.3).\n"
        "4. idealBuyer: A specific description of the perfect B2B customer.\n"
        "5. exclusions: Who should we NOT contact?\n"
        "6. valueProposition: One powerful sentence on why this product wins."
    )

    parts: list[dict] = [{"text": prompt}]
    for asset in product.assets:
        parts.append({"inline_data": {"mime_type": asset.mime_type, "data": asset.data}})

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents={"parts": parts},
        config=gtypes.GenerateContentConfig(
            **_thinking(DEFAULT_MODEL),
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "productIdentity": {"type": "string"},
                    "technicalSpecs":  {"type": "array", "items": {"type": "string"}},
                    "certifications":  {"type": "array", "items": {"type": "string"}},
                    "idealBuyer":      {"type": "string"},
                    "exclusions":      {"type": "string"},
                    "valueProposition":{"type": "string"},
                },
                "required": ["productIdentity", "idealBuyer", "certifications"],
            },
        ),
    )

    if not response.text:
        return FALLBACK_CONTEXT
    return StrategicContext.from_dict(json.loads(response.text))


# ---------------------------------------------------------------------------
# analyze_markets
# ---------------------------------------------------------------------------

def analyze_markets(
    product_name: str,
    product_description: str,
    continent: Optional[str] = None,
    countries: Optional[list[str]] = None,
    product_assets: Optional[list[ProductAsset]] = None,
    pre_computed_context: Optional[StrategicContext] = None,
    supplier_country: str = "China",
) -> list[RegionSuggestion]:
    """Port of analyzeMarkets()."""
    client = _client()

    targeting = "Analyze global trade data and trends."
    if continent and continent != "All":
        targeting += f" Focus strictly on markets within the continent of {continent}."
    if countries:
        targeting += (
            f" Prioritize analysis for these specific countries: {', '.join(countries)}. "
            "Fill remaining slots with high-potential neighbors to reach exactly 9 suggestions."
        )

    context_block = ""
    if pre_computed_context:
        ctx = pre_computed_context
        context_block = (
            f"\nMEMORY RETRIEVAL:\n"
            f"- Product Core: {ctx.product_identity}\n"
            f"- Key Certifications: {', '.join(ctx.certifications)}\n"
            f"- Specs: {', '.join(ctx.technical_specs)}\n"
        )

    prompt = (
        f'I am a supplier in {supplier_country} selling: "{product_name}".\n\n'
        f'PRODUCT SPECIFICATIONS:\n"{product_description or "Standard " + product_name}"\n\n'
        f"{context_block}\n"
        f"{targeting}\n\n"
        f"Task: Identify the top 9 best international regions/countries to target for exporting "
        f"this product from {supplier_country}.\n\n"
        "Return a JSON array of 9 suggestions."
    )

    parts = (
        [{"text": prompt}]
        if pre_computed_context
        else [{"text": prompt}] + [
            {"inline_data": {"mime_type": a.mime_type, "data": a.data}}
            for a in (product_assets or [])
        ]
    )

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents={"parts": parts},
        config=gtypes.GenerateContentConfig(
            **_thinking(DEFAULT_MODEL),
            response_mime_type="application/json",
            response_schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "region":      {"type": "string"},
                        "reason":      {"type": "string"},
                        "demandLevel": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    },
                },
            },
        ),
    )

    if not response.text:
        return []
    parsed = json.loads(response.text)
    return [
        RegionSuggestion(
            region=r.get("region", ""),
            reason=r.get("reason", ""),
            demand_level=r.get("demandLevel", "Medium"),
        )
        for r in (parsed if isinstance(parsed, list) else [])
    ]


# ---------------------------------------------------------------------------
# generate_market_report
# ---------------------------------------------------------------------------

def generate_market_report(product: ProductDetails, region: str) -> MarketReport:
    """Port of generateMarketReport(). Uses Google Search grounding."""
    client = _client()
    ctx = product.strategic_context
    ctx_str = (
        f"Product: {ctx.product_identity}. Specs: {', '.join(ctx.technical_specs)}. "
        f"Certs: {', '.join(ctx.certifications)}."
        if ctx else ""
    )

    prompt = (
        f'Conduct a PROFESSIONAL SUPPLIER INTELLIGENCE REPORT for exporting '
        f'"{product.name}" from {product.supplier_country or "China"} to "{region}".\n\n'
        f"Product Details: {product.description or product.name}\n"
        f"{('Technical Memory: ' + ctx_str) if ctx_str else ''}\n\n"
        "Use Google Search to find specific logistics, pricing, and compliance data.\n"
        "CRITICAL: Prioritize Official Government Websites for duty/regulation data.\n\n"
        "Required Sections: market overview, HS code, import duty %, ocean freight time, "
        "price structure, localization, key competitors, trade events, entry strategy, "
        "competitor market share %, growth trend, user segmentation.\n\n"
        "Return ONLY valid raw JSON (no markdown) with keys: region, overview, marketSize, "
        "buyingHabits, competitors (string array), regulations, entryStrategy, hsCode, "
        "importDuty, shippingTime, priceStructure, tradeShows (string array), localization, "
        "stats (competitorShare, growthTrend, userSegments — each array of {label, value})."
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
        raise RuntimeError(f"Empty model response for market report on {region}")

    parsed = extract_json_from_text(response.text)
    if not parsed:
        raise RuntimeError(f"Failed to parse JSON for market report on {region}")

    sources = [
        MarketReportSource(title=s["title"], url=s["url"])
        for s in extract_grounding_sources(response)
    ]

    raw_stats = parsed.get("stats", {})
    stats = MarketStats.from_dict(raw_stats) if raw_stats else None

    return MarketReport(
        region=parsed.get("region", region),
        overview=parsed.get("overview", "N/A"),
        market_size=parsed.get("marketSize", "N/A"),
        buying_habits=parsed.get("buyingHabits", "N/A"),
        competitors=parsed.get("competitors", []),
        regulations=parsed.get("regulations", "N/A"),
        entry_strategy=parsed.get("entryStrategy", "N/A"),
        hs_code=parsed.get("hsCode", "N/A"),
        import_duty=parsed.get("importDuty", "N/A"),
        shipping_time=parsed.get("shippingTime", "N/A"),
        price_structure=parsed.get("priceStructure", "N/A"),
        trade_shows=parsed.get("tradeShows", []),
        localization=parsed.get("localization", "N/A"),
        sources=sources,
        stats=stats,
    )


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


# ---------------------------------------------------------------------------
# generate_prospecting_message
# ---------------------------------------------------------------------------

def generate_prospecting_message(
    history: list[ChatMessage],
    lead: Lead,
    product_context: Optional[StrategicContext] = None,
) -> str:
    """Port of generateProspectingMessage(). SDR assistant chat for a specific lead."""
    client = _client()
    ctx = product_context or FALLBACK_CONTEXT
    md = lead.match_details

    system_instruction = (
        "You are an expert Sales Development Representative (SDR) and Prospecting Assistant.\n"
        "Your goal is to help the user craft the perfect outreach strategy for a specific lead.\n\n"
        f"LEAD CONTEXT:\n"
        f"Company: {lead.company_name}\n"
        f"Region: {lead.region}\n"
        f"Industry Fit: {md.industry_fit if md else 'N/A'}\n"
        f"Website: {lead.website or 'N/A'}\n"
        f"Address: {lead.address or lead.region}\n"
        f"Summary: {lead.summary or 'N/A'}\n"
        f"Current Status: {lead.status.value}\n"
        f"Next Steps / Notes: {lead.next_steps or 'None'}\n\n"
        f"PRODUCT CONTEXT:\n"
        f"Product: {ctx.product_identity}\n"
        f"Value Prop: {ctx.value_proposition}\n"
        f"Ideal Buyer: {ctx.ideal_buyer}\n\n"
        "STRATEGIC APPROACH:\n"
        "- Tone: Confident, professional, authoritative. Do NOT sound needy.\n"
        f"- Urgency: Frame as selecting key partners in {lead.region} — they are being evaluated.\n"
        "- Relevance: Connect product value prop directly to their business model.\n\n"
        "TASKS:\n"
        "1. Answer questions about the lead.\n"
        "2. Draft email sequences or LinkedIn messages using the 'Supply & Demand' urgency frame.\n"
        "3. Research the lead's current activities for outreach hooks.\n"
        "4. Advise on the best angle based on product context.\n\n"
        "Keep responses concise, professional, and actionable."
    )

    contents = [
        {"role": msg.role, "parts": [{"text": msg.content}]}
        for msg in history
    ]

    response = client.models.generate_content(
        model=GROUNDING_MODEL,
        contents=contents,
        config=gtypes.GenerateContentConfig(
            system_instruction=system_instruction,
            **_thinking(GROUNDING_MODEL),
            tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
        ),
    )

    text = response.text or "I couldn't generate a response. Please try again."

    sources = extract_grounding_sources(response)
    if sources:
        links = "\n".join(f"- [{s['title']}]({s['url']})" for s in sources)
        text += f"\n\n### Sources\n{links}"

    return text
