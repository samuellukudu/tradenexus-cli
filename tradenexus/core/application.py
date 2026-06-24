"""
tradenexus/core/application.py

Asynchronous Application-Led Discovery functions.
Supports progress streaming using async generators.
"""

from __future__ import annotations
import json
import uuid
import time
from typing import Optional, AsyncGenerator

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, GROUNDING_MODEL, build_thinking_config
from tradenexus.models import (
    ProductDetails, ProductRole, ProductApplication, CountryApplicationMap,
    Lead, LeadStatus, MatchDetails, Competitor, SocialProfile, InteractionLog,
    LeadQualification, LaneQualificationReport, StrategicContext
)
from tradenexus.utils import (
    extract_json_from_text,
    extract_grounding_urls,
    normalize_confidence
)


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


async def classify_product_role(product: ProductDetails, context: Optional[StrategicContext] = None) -> ProductRole:
    """Classifies a product's role in the supply chain and identifies the ecosystem around it."""
    client = _client()
    context_block = ""
    if context:
        context_block = f"Strategic context: {json.dumps(context.to_dict())}"

    prompt = (
        "You are an industrial product classifier for B2B trade.\n"
        "Classify this product's role in the supply chain and identify the ecosystem around it.\n\n"
        f"Product: {product.name}\n"
        f"Description: {product.description or product.name}\n"
        f"Supplier country: {product.supplier_country or 'unknown'}\n"
        f"{context_block}\n\n"
        "Return only valid JSON:\n"
        "{\n"
        '  "role": "<one of: finished system, machine or equipment, component, consumable, raw material, spare part, installation or service, software-enabled system>",\n'
        '  "resellerTypes": ["who resells this product"],\n'
        '  "installerTypes": ["who installs it"],\n'
        '  "operatorTypes": ["who operates/uses it"],\n'
        '  "maintainerTypes": ["who maintains/services it"],\n'
        '  "financierTypes": ["who finances purchases of it"]\n'
        "}"
    )

    response = await client.aio.models.generate_content(
        model=DEFAULT_MODEL,
        contents={"parts": [{"text": prompt}]},
        config=gtypes.GenerateContentConfig(
            **_thinking(DEFAULT_MODEL),
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": [
                            "finished system",
                            "machine or equipment",
                            "component",
                            "consumable",
                            "raw material",
                            "spare part",
                            "installation or service",
                            "software-enabled system"
                        ]
                    },
                    "resellerTypes": {"type": "array", "items": {"type": "string"}},
                    "installerTypes": {"type": "array", "items": {"type": "string"}},
                    "operatorTypes": {"type": "array", "items": {"type": "string"}},
                    "maintainerTypes": {"type": "array", "items": {"type": "string"}},
                    "financierTypes": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["role"]
            }
        )
    )

    if not response.text:
        return ProductRole(role="machine or equipment")

    parsed = extract_json_from_text(response.text) or {}
    return ProductRole.from_dict(parsed)


async def generate_application_map_generator(
    product: ProductDetails,
    country: str,
    product_role: ProductRole,
    context: Optional[StrategicContext] = None,
    past_maps: Optional[list[CountryApplicationMap]] = None,
    supplier_country: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Async generator to stream progress messages followed by the final application map."""
    yield json.dumps({"status": "starting", "message": f"Initiating application map for {country}..."})
    
    past_maps_context = "No past application maps available. Generate all applications from scratch."
    if past_maps:
        serialized_past_maps = [m.to_dict() for m in past_maps[-5:]]
        past_maps_context = (
            "Past application maps for reference (use as inspiration only — do NOT copy; "
            "generate fresh applications from current product+country):\n"
            f"{json.dumps(serialized_past_maps)}"
        )

    audience = product.target_audience or "All"
    if audience == "Distributors/Importers":
        audience_directive = (
            f"Focus on companies in {country} that IMPORT, DISTRIBUTE, WHOLESALE, or RETAIL this product. "
            "Look for trading companies, importers, distributors, dealers, retailers, wholesalers, and channel partners "
            "who buy from foreign suppliers to resell locally. Each application should describe a distribution or "
            f"retail context where this product would be stocked, resold, or re-distributed in {country}."
        )
    elif audience == "OEMs/Manufacturers":
        audience_directive = (
            f"Focus on companies in {country} that INCORPORATE this product as a component, input, or production asset "
            "into their own manufacturing or assembly. Look for OEMs, factories, and manufacturers that need this product "
            "for their production, assembly lines, or value-added processing. Each application should describe a "
            "manufacturing context where this product is an essential input."
        )
    elif audience == "End Users":
        audience_directive = (
            f"Focus on companies in {country} that directly USE or OPERATE this product in their business operations. "
            f"Each application must describe a real operational context where companies USE this product (not resell it)."
        )
    else:
        audience_directive = (
            f"Include ALL viable buyer types in {country} — end users who operate the product, distributors and importers "
            "who resell it, OEMs and manufacturers who incorporate it, retailers and wholesalers who stock it, and channel "
            "partners who specify or finance it. Generate a diverse mix of applications covering different buyer categories "
            "(resellers, end users, manufacturers). Ensure at least some applications target distribution and retail "
            "channels and some target operational end users."
        )

    sc_block = f"Strategic context: {json.dumps(context.to_dict())}" if context else ""

    yield json.dumps({"status": "researching", "message": f"Querying trade flows and industrial clusters in {country} using Google Search..."})

    prompt = (
        "You are an international trade analyst specializing in product-market decomposition.\n\n"
        f"Product: {product.name}\n"
        f"Description: {product.description or product.name}\n"
        f"Supplier country: {supplier_country or product.supplier_country or 'China'}\n"
        f"Target country: {country}\n"
        f"Product role: {json.dumps(product_role.to_dict())}\n"
        f"Target audience strategy: {audience}\n"
        f"{sc_block}\n\n"
        f"{past_maps_context}\n\n"
        f"Use Google Search to research {country}'s industries, infrastructure gaps, economic conditions, "
        "climate, regulations, and regional clusters relevant to this product.\n\n"
        f"Generate a country-specific application map. {audience_directive}\n\n"
        "For each application, provide:\n"
        '- name: specific application context (e.g. "commercial irrigation farms")\n'
        "- buyerTypes: specific company types operating in this context\n"
        f"- whyRelevant: why this product matters for this application in {country}\n"
        "- procurementTriggers: events that drive purchase decisions\n"
        f"- searchTerms: 3 actual Google search queries to find these companies in {country}\n"
        "- socialSearchTerms: 3 actual social-first queries for Facebook, Instagram, LinkedIn, TikTok, WhatsApp, Maps, or local marketplace surfaces\n"
        "- qualificationSignals: what confirms a company is a real fit\n"
        "- badFitSignals: what indicates a company is NOT a fit\n"
        "- decisionMakers: job titles/roles who make purchasing decisions\n"
        f"- confidence: 0-1 how confident you are this application is real for {country}\n"
        '- sourceType: "discovered" (or "adapted" if inspired by a past map)\n\n'
        "Then compute a priorityScore (0-1) for each application considering:\n"
        f"- demand likelihood in {country}\n"
        "- urgency of need\n"
        "- purchasing power of buyer types\n"
        "- import dependency (higher = more likely to import)\n"
        "- ease of finding these companies online\n"
        "- fit with supplier capability\n\n"
        "Generate at least 3 distinct applications, and at most 10. Focus on the most relevant ones. "
        "If you cannot find enough evidence for at least 3 applications, include lower-confidence ones "
        "with appropriate confidence scores.\n\n"
        "Return only a valid JSON object with this exact shape:\n"
        "{\n"
        '  "applications": [\n'
        "    {\n"
        '      "name": "...",\n'
        '      "buyerTypes": [...],\n'
        '      "whyRelevant": "...",\n'
        '      "procurementTriggers": [...],\n'
        '      "searchTerms": [...],\n'
        '      "socialSearchTerms": [...],\n'
        '      "qualificationSignals": [...],\n'
        '      "badFitSignals": [...],\n'
        '      "decisionMakers": [...],\n'
        '      "confidence": 0.9,\n'
        '      "priorityScore": 0.92,\n'
        '      "sourceType": "discovered"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    client = _client()
    response = await client.aio.models.generate_content(
        model=GROUNDING_MODEL,
        contents={"parts": [{"text": prompt}]},
        config=gtypes.GenerateContentConfig(
            **_thinking(GROUNDING_MODEL),
            tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
        )
    )

    yield json.dumps({"status": "extracting", "message": "Analyzing trade data and scoring discovered application lanes..."})

    if not response.text:
        res = CountryApplicationMap(
            product_name=product.name,
            country=country,
            product_role=product_role,
            applications=[],
            generated_at=time.time() * 1000
        )
    else:
        parsed = extract_json_from_text(response.text) or {}
        raw_apps = parsed.get("applications", []) if isinstance(parsed, dict) else []
        evidence = list(set(extract_grounding_urls(response)))

        applications = []
        for app in raw_apps:
            applications.append(
                ProductApplication(
                    id=str(uuid.uuid4()),
                    name=app.get("name", "Unknown Application"),
                    country=country,
                    buyer_types=app.get("buyerTypes", []),
                    why_relevant=app.get("whyRelevant", ""),
                    procurement_triggers=app.get("procurementTriggers", []),
                    search_terms=app.get("searchTerms", []),
                    social_search_terms=app.get("socialSearchTerms", []),
                    qualification_signals=app.get("qualificationSignals", []),
                    bad_fit_signals=app.get("badFitSignals", []),
                    decision_makers=app.get("decisionMakers", []),
                    priority_score=float(app.get("priorityScore", 0.5)),
                    confidence=float(app.get("confidence", 0.5)),
                    source_type=app.get("sourceType", "discovered"),
                    evidence=evidence
                )
            )
        applications.sort(key=lambda a: a.priority_score, reverse=True)

        res = CountryApplicationMap(
            product_name=product.name,
            country=country,
            product_role=product_role,
            applications=applications,
            generated_at=time.time() * 1000
        )

    yield json.dumps({"status": "complete", "message": "Application map generation complete!", "result": res.to_dict()})


async def generate_application_map(
    product: ProductDetails,
    country: str,
    product_role: ProductRole,
    context: Optional[StrategicContext] = None,
    past_maps: Optional[list[CountryApplicationMap]] = None,
    supplier_country: Optional[str] = None
) -> CountryApplicationMap:
    """Standard wrapper to await the full generation of the application map."""
    generator = generate_application_map_generator(product, country, product_role, context, past_maps, supplier_country)
    final_res = None
    async for chunk in generator:
        data = json.loads(chunk)
        if data.get("status") == "complete":
            final_res = CountryApplicationMap.from_dict(data["result"])
    return final_res or CountryApplicationMap(product_name=product.name, country=country, product_role=product_role, applications=[], generated_at=time.time()*1000)


async def search_application_lane_generator(
    product: ProductDetails,
    application: ProductApplication,
    lead_target: int
) -> AsyncGenerator[str, None]:
    """Async generator to stream progress messages followed by discovered leads."""
    yield json.dumps({"status": "starting", "message": f"Starting lead discovery on lane: {application.name}..."})
    
    product_role = product.product_role
    resellers = ", ".join(product_role.reseller_types) if product_role and product_role.reseller_types else "various"
    installers = ", ".join(product_role.installer_types) if product_role and product_role.installer_types else "various"
    operators = ", ".join(product_role.operator_types) if product_role and product_role.operator_types else "various"
    maintainers = ", ".join(product_role.maintainer_types) if product_role and product_role.maintainer_types else "various"
    financiers = ", ".join(product_role.financier_types) if product_role and product_role.financier_types else "various"

    targeting_directive = "Find companies that OPERATE in this application context."
    if product_role:
        role = product_role.role
        if role in ("component", "raw material"):
            targeting_directive = f"Find MANUFACTURERS and OEMs that INCORPORATE this {role} into their products. Target {operators or 'factories and production facilities'}."
        elif role in ("finished system", "machine or equipment"):
            targeting_directive = f"Find END USERS and OPERATORS of this {role}. Target {operators or 'facilities and operations'} that USE this equipment. Also include {resellers or 'dealers and distributors'} when they serve as the local purchasing channel."
        elif role in ("consumable", "spare part"):
            targeting_directive = f"Find COMPANIES that CONSUME or REPLACE this {role} regularly. Target {operators or 'maintenance and operations teams'}. Also include {maintainers or 'service providers'} who purchase on behalf of end users."
        elif role == "installation or service":
            targeting_directive = f"Find PROJECT OWNERS and CONTRACTORS that hire {installers or 'installation and service providers'}. Also include {financiers or 'project financiers'} who specify and procure these services."
        elif role == "software-enabled system":
            targeting_directive = f"Find ORGANIZATIONS that DEPLOY this {role}. Target {operators or 'IT and operations teams'} who both purchase and operate the system."

    audience = product.target_audience
    if audience and audience != "All":
        if audience == "Distributors/Importers":
            targeting_directive = (
                "Find DISTRIBUTORS, IMPORTERS, WHOLESALERS, DEALERS, RETAILERS, and CHANNEL PARTNERS in this application context. "
                "Look for trading companies that buy from foreign suppliers to resell locally. Prioritize companies whose "
                "business model is resale and distribution over end use."
            )
        elif audience == "OEMs/Manufacturers":
            targeting_directive = (
                "Find OEMs and MANUFACTURERS that incorporate this product into their own production. "
                "Look for factories, assembly operations, and industrial producers that use this product as an input or component. "
                "Prioritize companies with manufacturing or value-added processing operations."
            )
        elif audience == "End Users":
            targeting_directive = (
                "Find END USERS and OPERATORS that directly use this product in their business operations. "
                "Look for companies whose operations depend on this type of product. Prioritize companies that "
                "consume or operate the product themselves rather than reselling it."
            )

    queries = " | ".join(application.search_terms)
    yield json.dumps({"status": "searching", "message": f"Executing target lane search: {queries[:60]}..."})

    prompt = (
        f"You are a B2B lead discovery agent. {targeting_directive}\n\n"
        "═══════════════════════════════════════════\n"
        "PRODUCT & APPLICATION CONTEXT\n"
        "═══════════════════════════════════════════\n"
        f"Product: {product.name}\n"
        f"Description: {product.description or product.name}\n"
        f"Supplier country: {product.supplier_country or 'China'}\n"
        f"Target audience strategy: {audience or 'All'}\n"
        f"{f'Product role: {product_role.role} (resold by: {resellers}, installed by: {installers}, operated by: {operators})' if product_role else ''}\n\n"
        f"Application: {application.name}\n"
        f"Why this matters in {application.country}: {application.why_relevant}\n"
        f"Procurement triggers: {'; '.join(application.procurement_triggers)}\n\n"
        "═══════════════════════════════════════════\n"
        "🔴 MUST HAVE — reject any company missing these\n"
        "═══════════════════════════════════════════\n"
        f"{chr(10).join(['• ' + s for s in application.qualification_signals])}\n\n"
        "═══════════════════════════════════════════\n"
        "🟡 PREFERRED — rank higher if present\n"
        "═══════════════════════════════════════════\n"
        f"• Decision makers reachable: {', '.join(application.decision_makers)}\n"
        "• Active procurement cycle suggested by recent news, expansions, or tender participation\n"
        "• Physical operations verifiable via Google Maps, directory listings, or cross-platform profiles\n"
        f"• Buyer type matches: {', '.join(application.buyer_types)}\n\n"
        "═══════════════════════════════════════════\n"
        "🔵 SEARCH STRATEGY — execute in this order\n"
        "═══════════════════════════════════════════\n"
        f"1. PRIMARY: {queries}\n"
        f"2. SOCIAL-FIRST: {' | '.join(application.social_search_terms) if application.social_search_terms else f'site:facebook.com \"{product.name}\" \"{application.country}\"; site:instagram.com \"{product.name}\" \"{application.country}\"; site:linkedin.com/company \"{product.name}\" \"{application.country}\"'}\n"
        f"3. MAPS & DIRECTORIES: Google Maps business listings, chambers of commerce, industry association member directories in {application.country}\n\n"
        "═══════════════════════════════════════════\n"
        "⛔ AVOID — do NOT include companies that match these\n"
        "═══════════════════════════════════════════\n"
        f"{chr(10).join(['• ' + s for s in application.bad_fit_signals])}\n\n"
        f"OUTPUT — up to {lead_target} real companies\n"
        "═══════════════════════════════════════════\n"
        "Social profiles are valid source leads. A website is NOT required if social evidence shows clear business identity, "
        "target-country fit, application fit, contact/location hints, and activity/verification signals.\n\n"
        f"Return only a JSON array of up to {lead_target} objects. Each item must have: "
        "companyName, website, reason, confidenceScore (number), sourceUrl, googleMapsUrl, country, "
        "socialProfiles (array of {platform, url}), employeeCount, revenue, contactEmail, phoneNumber, "
        "address, tradeVolume, competitors (array of {name, strengths, weaknesses, displacementStrategy}), "
        "matchDetails ({industryFit, sizeFit, locationFit})."
    )

    client = _client()
    response = await client.aio.models.generate_content(
        model=GROUNDING_MODEL,
        contents={"parts": [{"text": prompt}]},
        config=gtypes.GenerateContentConfig(
            **_thinking(GROUNDING_MODEL),
            tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
        )
    )

    yield json.dumps({"status": "filtering", "message": "Parsing search results and verifying company addresses..."})

    leads = []
    if response.text:
        parsed = extract_json_from_text(response.text)
        raw_leads = parsed if isinstance(parsed, list) else []
        grounding_sources = list(set(extract_grounding_urls(response)))

        for lead in raw_leads:
            md_raw = lead.get("matchDetails") or {}
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
                for c in (lead.get("competitors") or [])
            ]
            social_profiles = [
                SocialProfile(platform=s.get("platform", ""), url=s.get("url", ""))
                for s in (lead.get("socialProfiles") or [])
            ]

            leads.append(
                Lead(
                    id=str(uuid.uuid4()),
                    company_name=lead.get("companyName") or lead.get("company_name") or "Unknown Company",
                    website=lead.get("website") if str(lead.get("website", "")).lower() != "n/a" else None,
                    region=application.country,
                    status=LeadStatus.DISCOVERED,
                    confidence_score=normalize_confidence(lead.get("confidenceScore") or lead.get("confidence_score")),
                    match_details=md,
                    summary=lead.get("reason"),
                    social_profiles=social_profiles,
                    employee_count=lead.get("employeeCount") or lead.get("employee_count"),
                    revenue=lead.get("revenue"),
                    contact_email=lead.get("contactEmail") or lead.get("contact_email"),
                    phone_number=lead.get("phoneNumber") or lead.get("phone_number"),
                    address=lead.get("address"),
                    source_url=lead.get("sourceUrl") or lead.get("source_url"),
                    google_maps_url=lead.get("googleMapsUrl") or lead.get("google_maps_url"),
                    trade_volume=lead.get("tradeVolume") or lead.get("trade_volume"),
                    competitors=competitors,
                    application_id=application.id,
                    application=application.name,
                    buyer_type=application.buyer_types[0] if application.buyer_types else None,
                    search_lane=application.search_terms[0] if application.search_terms else None,
                    sources=grounding_sources,
                    logs=[
                        InteractionLog(
                            timestamp=time.strftime("%X"),
                            actor="SYSTEM",
                            message=(
                                f"Lead discovered via application lane: {application.name}."
                                f"{chr(10) + 'Location: ' + lead.get('googleMapsUrl') if lead.get('googleMapsUrl') else ''}"
                            )
                        )
                    ]
                )
            )

    yield json.dumps({"status": "complete", "message": f"Discovered {len(leads)} leads!", "result": [l.to_dict() for l in leads]})


async def search_application_lane(
    product: ProductDetails,
    application: ProductApplication,
    lead_target: int
) -> list[Lead]:
    """Standard wrapper to await all discovered leads."""
    generator = search_application_lane_generator(product, application, lead_target)
    final_res = []
    async for chunk in generator:
        data = json.loads(chunk)
        if data.get("status") == "complete":
            final_res = [Lead.from_dict(l) for l in data["result"]]
    return final_res


async def qualify_leads(
    leads: list[Lead],
    application: ProductApplication,
    product_name: str
) -> LaneQualificationReport:
    """Qualifies a batch of leads against application qualification/bad-fit signals."""
    if not leads:
        return LaneQualificationReport(
            application_id=application.id,
            application_name=application.name,
            total_discovered=0,
            qualified=0,
            rejected=0,
            uncertain=0,
            qualifications=[]
        )

    client = _client()
    lead_list = "\n".join(
        f"{i + 1}. {l.company_name} | {l.website or 'no website'} | {l.summary or ''} | confidence: {l.confidence_score}"
        for i, l in enumerate(leads)
    )

    prompt = (
        "You are a lead qualification auditor. Your job is to SCREEN a batch of discovered leads against a specific application profile.\n\n"
        f"APPLICATION: {application.name}\n"
        f"COUNTRY: {application.country}\n"
        f"PRODUCT: {product_name}\n\n"
        "═══════════════════════════════════\n"
        "QUALIFICATION SIGNALS — a lead SHOULD match several of these:\n"
        f"{chr(10).join(['• ' + s for s in application.qualification_signals])}\n\n"
        "═══════════════════════════════════\n"
        "BAD-FIT SIGNALS — a lead matching ANY of these should be REJECTED:\n"
        f"{chr(10).join(['• ' + s for s in application.bad_fit_signals])}\n\n"
        "═══════════════════════════════════\n"
        f"DISCOVERED LEADS TO SCREEN:\n{lead_list}\n\n"
        "═══════════════════════════════════\n"
        "For EACH lead above, determine:\n"
        '- "qualified" — matches 2+ qualification signals AND triggers ZERO bad-fit signals\n'
        '- "rejected" — triggers ANY bad-fit signal OR matches zero qualification signals\n'
        '- "uncertain" — matches only 1 qualification signal with no bad-fit triggers, or insufficient information to decide\n\n'
        "Return ONLY a JSON object:\n"
        "{\n"
        '  "qualifications": [\n'
        "    {\n"
        '      "leadIndex": 1,\n'
        '      "result": "qualified",\n'
        '      "matchedSignals": ["signal text..."],\n'
        '      "triggeredBadFitSignals": [],\n'
        '      "reasoning": "one sentence why"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    response = await client.aio.models.generate_content(
        model=DEFAULT_MODEL,
        contents={"parts": [{"text": prompt}]},
        config=gtypes.GenerateContentConfig(
            **_thinking(DEFAULT_MODEL),
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "qualifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "leadIndex": {"type": "number"},
                                "result": {"type": "string", "enum": ["qualified", "rejected", "uncertain"]},
                                "matchedSignals": {"type": "array", "items": {"type": "string"}},
                                "triggeredBadFitSignals": {"type": "array", "items": {"type": "string"}},
                                "reasoning": {"type": "string"},
                            },
                            "required": ["leadIndex", "result", "reasoning"]
                        }
                    }
                },
                "required": ["qualifications"]
            }
        )
    )

    if not response.text:
        return LaneQualificationReport(
            application_id=application.id,
            application_name=application.name,
            total_discovered=len(leads),
            qualified=0,
            rejected=0,
            uncertain=0,
            qualifications=[]
        )

    parsed = extract_json_from_text(response.text) or {}
    raw_quals = parsed.get("qualifications", []) if isinstance(parsed, dict) else []

    qualifications = []
    for q in raw_quals:
        idx = int(q.get("leadIndex", 1)) - 1
        lead = leads[idx] if 0 <= idx < len(leads) else None
        qualifications.append(
            LeadQualification(
                lead_id=lead.id if lead else "",
                company_name=lead.company_name if lead else "Unknown",
                result=q.get("result", "uncertain"),
                matched_signals=q.get("matchedSignals", []),
                triggered_bad_fit_signals=q.get("triggeredBadFitSignals", []),
                reasoning=q.get("reasoning", "")
            )
        )

    qualified = sum(1 for q in qualifications if q.result == "qualified")
    rejected = sum(1 for q in qualifications if q.result == "rejected")
    uncertain = sum(1 for q in qualifications if q.result == "uncertain")

    return LaneQualificationReport(
        application_id=application.id,
        application_name=application.name,
        total_discovered=len(leads),
        qualified=qualified,
        rejected=rejected,
        uncertain=uncertain,
        qualifications=qualifications
    )


def allocate_lead_budget(
    applications: list[ProductApplication],
    total_budget: int
) -> dict[str, int]:
    """Allocates lead targets across multiple applications based on priority scores."""
    budget: dict[str, int] = {}
    total_score = sum(a.priority_score for a in applications)
    if total_score == 0 or len(applications) == 0:
        return budget

    min_per_lane = 1 if total_budget >= len(applications) else 0
    remaining = total_budget

    fracs: list[dict] = []
    for app in applications:
        raw = (total_budget * app.priority_score) / total_score
        alloc = max(min_per_lane, int(raw))
        budget[app.id] = alloc
        remaining -= alloc
        fracs.append({"id": app.id, "frac": raw - alloc})

    # If min_per_lane pushed us over budget, trim from lowest-priority apps
    if remaining < 0:
        overflow = -remaining
        # Walk applications in reverse (lowest priority first)
        for i in range(len(applications) - 1, -1, -1):
            if overflow <= 0:
                break
            app_id = applications[i].id
            if budget.get(app_id, 0) > 1:
                budget[app_id] -= 1
                overflow -= 1
        remaining = 0

    fracs.sort(key=lambda x: x["frac"], reverse=True)
    for f in fracs:
        if remaining <= 0:
            break
        budget[f["id"]] += 1
        remaining -= 1

    return budget
