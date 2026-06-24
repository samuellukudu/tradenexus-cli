"""
Pydantic models for FastAPI request/response schemas.

Field names use camelCase aliases (matching the Express API contract) while
Python code works with snake_case attributes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _camel_alias(snake: str) -> str:
    """product_identity -> productIdentity"""
    parts = snake.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=_camel_alias,
    )


# ---------------------------------------------------------------------------
# Product & Strategy
# ---------------------------------------------------------------------------

class ProductAsset(CamelModel):
    data: str = ""          # base64
    mime_type: str = ""
    file_name: str = ""


class StrategicContext(CamelModel):
    product_identity: str = ""
    technical_specs: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    ideal_buyer: str = ""
    exclusions: str = ""
    value_proposition: str = ""


class ProductRole(CamelModel):
    role: str
    reseller_types: list[str] = Field(default_factory=list)
    installer_types: list[str] = Field(default_factory=list)
    operator_types: list[str] = Field(default_factory=list)
    maintainer_types: list[str] = Field(default_factory=list)
    financier_types: list[str] = Field(default_factory=list)


class ProductApplication(CamelModel):
    id: str
    name: str
    country: str
    buyer_types: list[str] = Field(default_factory=list)
    why_relevant: str = ""
    procurement_triggers: list[str] = Field(default_factory=list)
    search_terms: list[str] = Field(default_factory=list)
    social_search_terms: list[str] = Field(default_factory=list)
    qualification_signals: list[str] = Field(default_factory=list)
    bad_fit_signals: list[str] = Field(default_factory=list)
    decision_makers: list[str] = Field(default_factory=list)
    priority_score: float = 0.5
    confidence: float = 0.5
    source_type: str = "discovered"
    evidence: list[str] = Field(default_factory=list)


class CountryApplicationMap(CamelModel):
    product_name: str
    country: str
    product_role: ProductRole
    applications: list[ProductApplication] = Field(default_factory=list)
    generated_at: float = 0.0


class ProductDetails(CamelModel):
    name: str = "Unknown Product"
    description: str = ""
    target_region: str = "Global"
    price_point: Optional[str] = None
    target_company_size: Optional[str] = None
    target_lead_count: int = 20
    target_audience: Optional[str] = None
    supplier_country: str = "China"
    assets: list[ProductAsset] = Field(default_factory=list)
    strategic_context: Optional[StrategicContext] = None
    product_role: Optional[ProductRole] = None


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(CamelModel):
    role: str  # "user" | "model"
    content: str
    timestamp: Optional[str] = None


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------

class MatchDetails(CamelModel):
    industry_fit: str = ""
    size_fit: str = ""
    location_fit: str = ""


class SocialProfile(CamelModel):
    platform: str = ""
    url: str = ""


class Competitor(CamelModel):
    name: str = ""
    strengths: str = ""
    weaknesses: str = ""
    displacement_strategy: str = ""


class InteractionLog(CamelModel):
    timestamp: str = ""
    actor: str = "SYSTEM"  # "AGENT" | "CLIENT" | "SYSTEM"
    message: str = ""
    tactic: Optional[str] = None


class Lead(CamelModel):
    id: str = ""
    company_name: str = ""
    region: str = ""
    status: str = "DISCOVERED"  # LeadStatus enum value
    confidence_score: int = 0
    logs: list[InteractionLog] = Field(default_factory=list)
    website: Optional[str] = None
    match_details: Optional[MatchDetails] = None
    summary: Optional[str] = None
    social_profiles: list[SocialProfile] = Field(default_factory=list)
    employee_count: Optional[str] = None
    revenue: Optional[str] = None
    contact_email: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    source_url: Optional[str] = None
    google_maps_url: Optional[str] = None
    search_vector: Optional[str] = None
    trade_volume: Optional[str] = None
    manufacturing_volume: Optional[str] = None
    next_steps: Optional[str] = None
    competitors: list[Competitor] = Field(default_factory=list)
    verification_status: Optional[str] = None
    verification_notes: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    # these hold arbitrary dicts/lists from agent pipeline phases
    evidence: list[dict] = Field(default_factory=list)
    social_discovery: list[dict] = Field(default_factory=list)
    verification: Optional[dict] = None
    score_breakdown: Optional[dict] = None
    recommendations: list[dict] = Field(default_factory=list)
    outreach_drafts: list[dict] = Field(default_factory=list)
    last_agent_action: Optional[str] = None
    # Application context tagging
    application_id: Optional[str] = None
    application: Optional[str] = None
    buyer_type: Optional[str] = None
    search_lane: Optional[str] = None


# ---------------------------------------------------------------------------
# Market Intelligence
# ---------------------------------------------------------------------------

class StatPoint(CamelModel):
    label: str = ""
    value: float = 0


class MarketStats(CamelModel):
    competitor_share: list[StatPoint] = Field(default_factory=list)
    growth_trend: list[StatPoint] = Field(default_factory=list)
    user_segments: list[StatPoint] = Field(default_factory=list)


class MarketReportSource(CamelModel):
    title: str = ""
    url: str = ""


class MarketReport(CamelModel):
    region: str = ""
    overview: str = ""
    market_size: str = ""
    buying_habits: str = ""
    competitors: list[str] = Field(default_factory=list)
    regulations: str = ""
    entry_strategy: str = ""
    hs_code: str = ""
    import_duty: str = ""
    shipping_time: str = ""
    price_structure: str = ""
    trade_shows: list[str] = Field(default_factory=list)
    localization: str = ""
    sources: list[MarketReportSource] = Field(default_factory=list)
    stats: Optional[MarketStats] = None


class RegionSuggestion(CamelModel):
    region: str = ""
    reason: str = ""
    demand_level: str = "Medium"


# ---------------------------------------------------------------------------
# Agent pipeline types
# ---------------------------------------------------------------------------

class VerificationCheck(CamelModel):
    id: str = ""
    type: str = "LOCATION"
    status: str = "UNKNOWN"  # PASS | FAIL | WARNING | UNKNOWN
    confidence: float = 0.5
    notes: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class LeadVerification(CamelModel):
    status: str = "UNVERIFIED"  # VERIFIED | PARTIAL | FAILED | UNVERIFIED
    confidence: float = 0.0
    checks: list[VerificationCheck] = Field(default_factory=list)
    updated_at: float = 0.0


class LeadScoreBreakdown(CamelModel):
    overall: int = 50
    location_fit: int = 50
    product_fit: int = 50
    buyer_type_fit: int = 50
    company_size_fit: int = 50
    evidence_quality: int = 50
    social_activity: int = 50
    contactability: int = 50
    competitive_opportunity: int = 50
    freshness: int = 50
    rationale: str = ""
    updated_at: float = 0.0


class AgentRecommendation(CamelModel):
    id: str = ""
    type: str = "USER_REVIEW"
    priority: str = "MEDIUM"
    title: str = ""
    reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: float = 0.0


class ClosingStrategy(CamelModel):
    type: str = "DIRECT_VALUE_PITCH"
    rationale: str = ""
    key_talking_points: list[str] = Field(default_factory=list)
    evidence_to_highlight: list[str] = Field(default_factory=list)
    recommended_platform: str = "cold_email"
    confidence: int = 70
    generated_at: float = 0.0


class OutreachDraft(CamelModel):
    id: str = ""
    type: str = "cold_email"
    body: str = ""
    subject: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: float = 0.0
    approved: bool = False


class OutreachSequenceStep(CamelModel):
    step: int = 0
    type: str = "cold_email"
    timing: str = ""
    goal: str = ""
    draft_id: Optional[str] = None


class OutreachSequence(CamelModel):
    id: str = ""
    lead_id: str = ""
    strategy_type: str = ""
    steps: list[OutreachSequenceStep] = Field(default_factory=list)
    total_days: int = 14
    rationale: str = ""
    generated_at: float = 0.0


class LeadQualification(CamelModel):
    lead_id: str = ""
    company_name: str = ""
    result: str = "uncertain"
    matched_signals: list[str] = Field(default_factory=list)
    triggered_bad_fit_signals: list[str] = Field(default_factory=list)
    reasoning: str = ""


class LaneQualificationReport(CamelModel):
    application_id: str = ""
    application_name: str = ""
    total_discovered: int = 0
    qualified: int = 0
    rejected: int = 0
    uncertain: int = 0
    qualifications: list[LeadQualification] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Social Discovery
# ---------------------------------------------------------------------------

class SocialProfileEvidence(CamelModel):
    id: str = ""
    source_type: str = "other"
    url: str = ""
    title: Optional[str] = None
    snippet: Optional[str] = None
    extracted_fields: dict = Field(default_factory=dict)
    confidence: float = 0.5
    found_at: float = 0.0
    found_by: str = "socialDiscovery"
    validation_status: str = "UNVERIFIED"
    platform: str = "other"
    handle: Optional[str] = None
    is_official_likely: bool = False
    profile_type: str = "unknown"
    activity_level: str = "UNKNOWN"
    activity_evidence: Optional[str] = None
    contact_hints: list[str] = Field(default_factory=list)
    relevance_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Request bodies  (thin wrappers — match Express req.body shapes exactly)
# ---------------------------------------------------------------------------

class ProspectingMessageRequest(CamelModel):
    history: list[ChatMessage] = Field(default_factory=list)
    lead: Lead
    product_context: Optional[StrategicContext] = Field(default=None, alias="productContext")


class ExtractSearchStrategyRequest(CamelModel):
    product: ProductDetails


class AnalyzeMarketsRequest(CamelModel):
    product_name: str = Field(alias="productName")
    product_description: str = Field(default="", alias="productDescription")
    continent: Optional[str] = None
    countries: Optional[list[str]] = None
    product_assets: Optional[list[ProductAsset]] = Field(default=None, alias="productAssets")
    pre_computed_context: Optional[StrategicContext] = Field(default=None, alias="preComputedContext")
    supplier_country: str = Field(default="China", alias="supplierCountry")


class MarketReportRequest(CamelModel):
    product: ProductDetails
    region: str


class SearchLeadsRequest(CamelModel):
    product: ProductDetails


class VerifyLeadRequest(CamelModel):
    lead: Lead
    product: ProductDetails


class SocialDiscoveryCompanyRequest(CamelModel):
    company_name: str = Field(alias="companyName")
    region: str
    website: Optional[str] = None
    product_context: Optional[StrategicContext] = Field(default=None, alias="productContext")


class SocialDiscoveryRegionRequest(CamelModel):
    product_name: str = Field(alias="productName")
    region: str
    product_context: Optional[StrategicContext] = Field(default=None, alias="productContext")


class AgentVerifyLeadRequest(CamelModel):
    lead: Lead
    product: Optional[ProductDetails] = None


class AgentScoreLeadRequest(CamelModel):
    lead: Lead
    product: Optional[ProductDetails] = None


class NextBestActionRequest(CamelModel):
    lead: Lead


class ClosingStrategyRequest(CamelModel):
    lead: Lead
    product: Optional[ProductDetails] = None


class OutreachDraftRequest(CamelModel):
    lead: Lead
    type: str  # cold_email | linkedin_connection | linkedin_followup | whatsapp_short | tradeshow_intro | distributor_pitch
    strategy: ClosingStrategy
    context: Optional[StrategicContext] = None


class FollowUpSequenceRequest(CamelModel):
    lead: Lead
    draft_id: str = Field(alias="draftId")
    strategy: ClosingStrategy


class ClassifyProductRoleRequest(CamelModel):
    product: ProductDetails
    context: Optional[StrategicContext] = None


class GenerateApplicationMapRequest(CamelModel):
    product: ProductDetails
    country: str
    product_role: ProductRole = Field(alias="productRole")
    context: Optional[StrategicContext] = None
    past_maps: Optional[list[CountryApplicationMap]] = Field(default=None, alias="pastMaps")
    supplier_country: Optional[str] = Field(default=None, alias="supplierCountry")


class SearchApplicationLaneRequest(CamelModel):
    product: ProductDetails
    application: ProductApplication
    lead_target: int = Field(alias="leadTarget")


class QualifyLeadsRequest(CamelModel):
    leads: list[Lead]
    application: ProductApplication
    product_name: str = Field(alias="productName")
