"""
POST /api/agent/*  — Agent pipeline endpoints (social discovery, verification,
scoring, next-best-action, outreach drafting, follow-up planning).

Each endpoint delegates to existing tradenexus.agent modules.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter

from tradenexus.agent.discovery.social import (
    discover_leads_from_social,
    discover_social_for_company,
)
from tradenexus.agent.discovery.social_to_lead import social_profiles_to_leads
from tradenexus.agent.outreach.drafting import generate_outreach_draft
from tradenexus.agent.outreach.followup import plan_follow_up_sequence
from tradenexus.agent.outreach.strategy import generate_closing_strategy
from tradenexus.agent.planner.actions import recommend_next_actions
from tradenexus.agent.scoring.lead import score_lead
from tradenexus.agent.verification.lead import verify_lead as agent_verify_lead
from tradenexus.api.schemas import (
    AgentScoreLeadRequest,
    AgentVerifyLeadRequest,
    ClosingStrategyRequest,
    FollowUpSequenceRequest,
    NextBestActionRequest,
    OutreachDraftRequest,
    SocialDiscoveryCompanyRequest,
    SocialDiscoveryRegionRequest,
    SocialProfileEvidence,
)
from tradenexus.models import (
    Lead,
    LeadStatus,
    ProductDetails,
    StrategicContext,
    ProductRole,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# conversion helpers (shared with ai router — kept local for module independence)
# ---------------------------------------------------------------------------

def _to_snake(d: dict) -> dict:
    if not isinstance(d, dict):
        return d
    result: dict[str, Any] = {}
    for k, v in d.items():
        snake = "".join(
            f"_{c.lower()}" if c.isupper() and i > 0 else c.lower()
            for i, c in enumerate(k)
        )
        snake = snake.lstrip("_")
        if isinstance(v, dict):
            result[snake] = _to_snake(v)
        elif isinstance(v, list):
            result[snake] = [
                _to_snake(item) if isinstance(item, dict) else item for item in v
            ]
        else:
            result[snake] = v
    return result


def _to_camel(d: dict) -> dict:
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


def _mk_lead(data: dict) -> Lead:
    from tradenexus.models import (
        ChatMessage,
        Competitor,
        InteractionLog,
        MatchDetails,
        SocialProfile,
    )
    d = _to_snake(data)
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


def _mk_product(data: dict) -> ProductDetails:
    d = _to_snake(data)
    from tradenexus.models import ProductAsset
    assets = [ProductAsset(**a) for a in (d.get("assets") or [])]
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


def _mk_context(data: dict | None) -> StrategicContext | None:
    if not data:
        return None
    return StrategicContext.from_dict(data)


def _profile_to_dict(p) -> dict:
    """Convert a SocialProfileEvidence dataclass instance to camelCase dict."""
    d = asdict(p)
    return _to_camel(d)


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------


@router.post("/social-discovery/company")
async def social_discovery_company(body: SocialDiscoveryCompanyRequest):
    ctx = _mk_context(
        body.product_context.model_dump(by_alias=False) if body.product_context else None
    )
    profiles = discover_social_for_company(
        company_name=body.company_name,
        region=body.region,
        website=body.website,
        product_context=ctx,
    )
    return {"profiles": [_profile_to_dict(p) for p in profiles]}


@router.post("/social-discovery/region")
async def social_discovery_region(body: SocialDiscoveryRegionRequest):
    ctx = _mk_context(
        body.product_context.model_dump(by_alias=False) if body.product_context else None
    )
    profiles = discover_leads_from_social(
        product_name=body.product_name,
        region=body.region,
        product_context=ctx,
    )
    leads = social_profiles_to_leads(profiles, body.region)
    return {
        "profiles": [_profile_to_dict(p) for p in profiles],
        "leads": [lead.to_dict() for lead in leads],
    }


@router.post("/verify-lead")
async def verify_lead_route(body: AgentVerifyLeadRequest):
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    product = _mk_product(body.product.model_dump(by_alias=False)) if body.product else None
    verification = agent_verify_lead(lead, product)
    return {"verification": _to_camel(asdict(verification))}


@router.post("/score-lead")
async def score_lead_route(body: AgentScoreLeadRequest):
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    product = _mk_product(body.product.model_dump(by_alias=False)) if body.product else None
    score = score_lead(lead, product)
    return {"score": _to_camel(asdict(score))}


@router.post("/next-best-action")
async def next_best_action(body: NextBestActionRequest):
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    recommendations = recommend_next_actions(lead)
    return {"recommendations": [_to_camel(asdict(r)) for r in recommendations]}


@router.post("/closing-strategy")
async def closing_strategy(body: ClosingStrategyRequest):
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    product = _mk_product(body.product.model_dump(by_alias=False)) if body.product else None
    strategy = generate_closing_strategy(lead, product)
    return {"strategy": _to_camel(asdict(strategy))}


@router.post("/outreach-draft")
async def outreach_draft(body: OutreachDraftRequest):
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    strategy_dc = _to_snake(body.strategy.model_dump(by_alias=False))
    from tradenexus.agent.types import ClosingStrategy as DC_ClosingStrategy
    strategy = DC_ClosingStrategy(
        type=strategy_dc.get("type", "DIRECT_VALUE_PITCH"),
        rationale=strategy_dc.get("rationale", ""),
        key_talking_points=strategy_dc.get("key_talking_points") or [],
        evidence_to_highlight=strategy_dc.get("evidence_to_highlight") or [],
        recommended_platform=strategy_dc.get("recommended_platform", "cold_email"),
        confidence=strategy_dc.get("confidence", 70),
        generated_at=strategy_dc.get("generated_at", 0.0),
    )
    ctx = _mk_context(
        body.context.model_dump(by_alias=False) if body.context else None
    )
    draft = generate_outreach_draft(lead, body.type, strategy, ctx)
    return {"draft": _to_camel(asdict(draft))}


@router.post("/follow-up-sequence")
async def follow_up_sequence(body: FollowUpSequenceRequest):
    lead = _mk_lead(body.lead.model_dump(by_alias=False))
    strategy_dc_data = _to_snake(body.strategy.model_dump(by_alias=False))
    from tradenexus.agent.types import ClosingStrategy as DC_ClosingStrategy
    strategy = DC_ClosingStrategy(
        type=strategy_dc_data.get("type", "DIRECT_VALUE_PITCH"),
        rationale=strategy_dc_data.get("rationale", ""),
        key_talking_points=strategy_dc_data.get("key_talking_points") or [],
        evidence_to_highlight=strategy_dc_data.get("evidence_to_highlight") or [],
        recommended_platform=strategy_dc_data.get("recommended_platform", "cold_email"),
        confidence=strategy_dc_data.get("confidence", 70),
        generated_at=strategy_dc_data.get("generated_at", 0.0),
    )
    sequence = plan_follow_up_sequence(lead, body.draft_id, strategy)
    return {"sequence": _to_camel(asdict(sequence))}
