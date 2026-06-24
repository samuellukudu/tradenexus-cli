"""
POST /api/ai/*  — AI-powered endpoints (prospecting, market analysis, lead discovery).

Each endpoint delegates to the existing tradenexus.core / tradenexus.models layer.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from tradenexus.api.schemas import (
    AnalyzeMarketsRequest,
    ExtractSearchStrategyRequest,
    MarketReportRequest,
    ProspectingMessageRequest,
    SearchLeadsRequest,
    VerifyLeadRequest,
    ClassifyProductRoleRequest,
    GenerateApplicationMapRequest,
    SearchApplicationLaneRequest,
    QualifyLeadsRequest,
)
from tradenexus.core.context import extract_search_strategy_from_assets
from tradenexus.core.leads import search_for_leads, verify_lead
from tradenexus.core.markets import analyze_markets, generate_market_report
from tradenexus.core.prospecting import generate_prospecting_message
from tradenexus.core.application import (
    classify_product_role,
    generate_application_map,
    search_application_lane,
    qualify_leads,
    generate_application_map_generator,
    search_application_lane_generator,
)
from tradenexus.models import (
    ChatMessage,
    Lead,
    LeadStatus,
    ProductAsset,
    ProductDetails,
    StrategicContext,
    ProductRole,
    ProductApplication,
    CountryApplicationMap,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# conversion helpers
# ---------------------------------------------------------------------------

def _to_snake(d: dict) -> dict:
    """Recursively convert camelCase keys to snake_case in a dict."""
    if not isinstance(d, dict):
        return d
    result: dict[str, Any] = {}
    for k, v in d.items():
        snake = "".join(
            f"_{c.lower()}" if c.isupper() and i > 0 else c.lower()
            for i, c in enumerate(k)
        )
        # fix double underscores from consecutive caps
        snake = snake.lstrip("_")
        result[snake] = _to_snake(v) if isinstance(v, dict) else v
        if isinstance(v, list):
            result[snake] = [_to_snake(item) if isinstance(item, dict) else item for item in v]
    return result


def _to_camel(d: dict) -> dict:
    """Recursively convert snake_case keys to camelCase."""
    if not isinstance(d, dict):
        return d
    result: dict[str, Any] = {}
    for k, v in d.items():
        parts = k.split("_")
        camel = parts[0] + "".join(p.title() for p in parts[1:])
        if isinstance(v, dict):
            result[camel] = _to_camel(v)
        elif isinstance(v, list):
            result[camel] = [
                _to_camel(item) if isinstance(item, dict) else item for item in v
            ]
        else:
            result[camel] = v
    return result


def _mk_product(data: dict) -> ProductDetails:
    d = _to_snake(data)
    assets = [
        ProductAsset(**a) for a in (d.get("assets") or [])
    ]
    ctx = d.get("strategic_context")
    role_raw = d.get("product_role")
    product_role = ProductRole.from_dict(role_raw) if role_raw else None
    return ProductDetails(
        name=d.get("name", "Unknown Product"),
        description=d.get("description", ""),
        target_region=d.get("target_region", "Global"),
        price_point=d.get("price_point"),
        target_company_size=d.get("target_company_size"),
        target_lead_count=d.get("target_lead_count", 20),
        target_audience=d.get("target_audience"),
        supplier_country=d.get("supplier_country", "China"),
        assets=assets,
        strategic_context=StrategicContext.from_dict(ctx) if ctx else None,
        product_role=product_role,
    )


def _mk_lead(data: dict) -> Lead:
    d = _to_snake(data)
    from tradenexus.models import Competitor, InteractionLog, MatchDetails, SocialProfile
    return Lead(
        id=d.get("id", ""),
        company_name=d.get("company_name", ""),
        region=d.get("region", ""),
        status=LeadStatus(d.get("status", "DISCOVERED")),
        confidence_score=d.get("confidence_score", 0),
        logs=[InteractionLog(**log) for log in (d.get("logs") or [])],
        website=d.get("website"),
        match_details=MatchDetails(**(d.get("match_details") or {})),
        summary=d.get("summary"),
        social_profiles=[SocialProfile(**sp) for sp in (d.get("social_profiles") or [])],
        employee_count=d.get("employee_count"),
        revenue=d.get("revenue"),
        contact_email=d.get("contact_email"),
        phone_number=d.get("phone_number"),
        address=d.get("address"),
        source_url=d.get("source_url"),
        google_maps_url=d.get("google_maps_url"),
        search_vector=d.get("search_vector"),
        trade_volume=d.get("trade_volume"),
        manufacturing_volume=d.get("manufacturing_volume"),
        next_steps=d.get("next_steps"),
        competitors=[Competitor(**c) for c in (d.get("competitors") or [])],
        verification_status=d.get("verification_status"),
        verification_notes=d.get("verification_notes"),
        sources=d.get("sources") or [],
        chat_history=[ChatMessage(**msg) for msg in (d.get("chat_history") or [])],
        evidence=d.get("evidence") or [],
        social_discovery=d.get("social_discovery") or [],
        verification=d.get("verification"),
        score_breakdown=d.get("score_breakdown"),
        recommendations=d.get("recommendations") or [],
        outreach_drafts=d.get("outreach_drafts") or [],
        last_agent_action=d.get("last_agent_action"),
        application_id=d.get("application_id"),
        application=d.get("application"),
        buyer_type=d.get("buyer_type"),
        search_lane=d.get("search_lane"),
    )


def _mk_product_role(data: dict) -> ProductRole:
    d = _to_snake(data)
    return ProductRole(
        role=d.get("role", "machine or equipment"),
        reseller_types=d.get("reseller_types") or [],
        installer_types=d.get("installer_types") or [],
        operator_types=d.get("operator_types") or [],
        maintainer_types=d.get("maintainer_types") or [],
        financier_types=d.get("financier_types") or [],
    )


def _mk_product_application(data: dict) -> ProductApplication:
    d = _to_snake(data)
    return ProductApplication(
        id=d.get("id", ""),
        name=d.get("name", "Unknown Application"),
        country=d.get("country", ""),
        buyer_types=d.get("buyer_types") or [],
        why_relevant=d.get("why_relevant", ""),
        procurement_triggers=d.get("procurement_triggers") or [],
        search_terms=d.get("search_terms") or [],
        social_search_terms=d.get("social_search_terms") or [],
        qualification_signals=d.get("qualification_signals") or [],
        bad_fit_signals=d.get("bad_fit_signals") or [],
        decision_makers=d.get("decision_makers") or [],
        priority_score=float(d.get("priority_score", 0.5)),
        confidence=float(d.get("confidence", 0.5)),
        source_type=d.get("source_type", "discovered"),
        evidence=d.get("evidence") or [],
    )


def _mk_country_application_map(data: dict) -> CountryApplicationMap:
    d = _to_snake(data)
    role_raw = d.get("product_role")
    role = _mk_product_role(role_raw) if role_raw else ProductRole("machine or equipment")
    apps = [_mk_product_application(a) for a in (d.get("applications") or [])]
    return CountryApplicationMap(
        product_name=d.get("product_name", ""),
        country=d.get("country", ""),
        product_role=role,
        applications=apps,
        generated_at=float(d.get("generated_at", 0.0)),
    )


def _mk_chat_messages(data: list[dict]) -> list[ChatMessage]:
    return [ChatMessage(**_to_snake(msg)) for msg in data]


def _mk_strategic_context(data: dict | None) -> StrategicContext | None:
    if not data:
        return None
    return StrategicContext.from_dict(data)


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

@router.post("/prospecting-message")
async def prospecting_message(body: ProspectingMessageRequest):
    history = _mk_chat_messages([h.model_dump(by_alias=False) for h in body.history])
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    ctx = _mk_strategic_context(
        body.product_context.model_dump(by_alias=False) if body.product_context else None
    )
    text = generate_prospecting_message(history, lead, ctx)
    return {"text": text}


@router.post("/extract-search-strategy")
async def extract_search_strategy(body: ExtractSearchStrategyRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    ctx = extract_search_strategy_from_assets(product)
    return {"context": ctx.to_dict()}


@router.post("/analyze-markets")
async def analyze_markets_route(body: AnalyzeMarketsRequest):
    assets = None
    if body.product_assets:
        assets = [
            ProductAsset(data=a.data, mime_type=a.mime_type, file_name=a.file_name)
            for a in body.product_assets
        ]
    ctx = None
    if body.pre_computed_context:
        ctx = StrategicContext.from_dict(
            body.pre_computed_context.model_dump(by_alias=False)
        )

    suggestions = analyze_markets(
        product_name=body.product_name,
        product_description=body.product_description,
        continent=body.continent,
        countries=body.countries,
        product_assets=assets,
        pre_computed_context=ctx,
        supplier_country=body.supplier_country,
    )
    return {"suggestions": [_to_camel(asdict(s)) for s in suggestions]}


@router.post("/market-report")
async def market_report_route(body: MarketReportRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    report = generate_market_report(product, body.region)
    return {"report": _to_camel(asdict(report))}


@router.post("/search-leads")
def search_leads_route(body: SearchLeadsRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    leads = search_for_leads(product)
    return {"leads": [lead.to_dict() for lead in leads]}


@router.post("/verify-lead")
async def verify_lead_route(body: VerifyLeadRequest):
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    product = _mk_product(body.product.model_dump(by_alias=False))
    result = verify_lead(lead, product)
    return {"result": result}


@router.post("/classify-product-role")
async def classify_product_role_route(body: ClassifyProductRoleRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    ctx = _mk_strategic_context(
        body.context.model_dump(by_alias=False) if body.context else None
    )
    res = await classify_product_role(product, ctx)
    return {"productRole": _to_camel(asdict(res))}


@router.post("/application-map")
async def application_map_route(body: GenerateApplicationMapRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    role = _mk_product_role(body.product_role.model_dump(by_alias=False))
    ctx = _mk_strategic_context(
        body.context.model_dump(by_alias=False) if body.context else None
    )
    past_maps = None
    if body.past_maps:
        past_maps = [_mk_country_application_map(m.model_dump(by_alias=False)) for m in body.past_maps]
    res = await generate_application_map(
        product=product,
        country=body.country,
        product_role=role,
        context=ctx,
        past_maps=past_maps,
        supplier_country=body.supplier_country
    )
    return {"applicationMap": _to_camel(asdict(res))}


@router.post("/application-map/stream")
async def application_map_stream_route(body: GenerateApplicationMapRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    role = _mk_product_role(body.product_role.model_dump(by_alias=False))
    ctx = _mk_strategic_context(
        body.context.model_dump(by_alias=False) if body.context else None
    )
    past_maps = None
    if body.past_maps:
        past_maps = [_mk_country_application_map(m.model_dump(by_alias=False)) for m in body.past_maps]
    
    async def sse_generator():
        generator = generate_application_map_generator(
            product=product,
            country=body.country,
            product_role=role,
            context=ctx,
            past_maps=past_maps,
            supplier_country=body.supplier_country
        )
        async for chunk in generator:
            yield f"data: {chunk}\n\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.post("/search-application-lane")
async def search_application_lane_route(body: SearchApplicationLaneRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    app = _mk_product_application(body.application.model_dump(by_alias=False))
    res_leads = await search_application_lane(product, app, body.lead_target)
    return {"leads": [l.to_dict() for l in res_leads]}


@router.post("/search-application-lane/stream")
async def search_application_lane_stream_route(body: SearchApplicationLaneRequest):
    product = _mk_product(body.product.model_dump(by_alias=False))
    app = _mk_product_application(body.application.model_dump(by_alias=False))
    
    async def sse_generator():
        generator = search_application_lane_generator(product, app, body.lead_target)
        async for chunk in generator:
            yield f"data: {chunk}\n\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.post("/qualify-leads")
async def qualify_leads_route(body: QualifyLeadsRequest):
    leads = [_mk_lead(l.model_dump(by_alias=False)) for l in body.leads]
    app = _mk_product_application(body.application.model_dump(by_alias=False))
    report = await qualify_leads(leads, app, body.product_name)
    return {"report": _to_camel(asdict(report))}
