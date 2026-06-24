"""
tradenexus/models.py

Python dataclasses mirroring types.ts from tradenexus-ai-sales-agent.
All fields are kept intentionally loose (Optional) to match the JS duck-typing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Product / Context
# ---------------------------------------------------------------------------

@dataclass
class ProductAsset:
    data: str          # base64-encoded, no data-URL prefix
    mime_type: str
    file_name: Optional[str] = None


@dataclass
class StrategicContext:
    product_identity: str = "Unspecified Product"
    technical_specs: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    ideal_buyer: str = "General Importers"
    exclusions: str = "None"
    value_proposition: str = "Standard Quality"

    @classmethod
    def from_dict(cls, d: dict) -> "StrategicContext":
        return cls(
            product_identity=d.get("productIdentity", "Unspecified Product"),
            technical_specs=d.get("technicalSpecs", []),
            certifications=d.get("certifications", []),
            ideal_buyer=d.get("idealBuyer", "General Importers"),
            exclusions=d.get("exclusions", "None"),
            value_proposition=d.get("valueProposition", "Standard Quality"),
        )

    def to_dict(self) -> dict:
        return {
            "productIdentity": self.product_identity,
            "technicalSpecs": self.technical_specs,
            "certifications": self.certifications,
            "idealBuyer": self.ideal_buyer,
            "exclusions": self.exclusions,
            "valueProposition": self.value_proposition,
        }


TargetAudienceType = str  # 'Distributors/Importers' | 'OEMs/Manufacturers' | 'End Users' | 'All'


@dataclass
class ProductRole:
    role: str
    reseller_types: list[str] = field(default_factory=list)
    installer_types: list[str] = field(default_factory=list)
    operator_types: list[str] = field(default_factory=list)
    maintainer_types: list[str] = field(default_factory=list)
    financier_types: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ProductRole":
        return cls(
            role=d.get("role", "machine or equipment"),
            reseller_types=d.get("resellerTypes", []),
            installer_types=d.get("installerTypes", []),
            operator_types=d.get("operatorTypes", []),
            maintainer_types=d.get("maintainerTypes", []),
            financier_types=d.get("financierTypes", []),
        )

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "resellerTypes": self.reseller_types,
            "installerTypes": self.installer_types,
            "operatorTypes": self.operator_types,
            "maintainerTypes": self.maintainer_types,
            "financierTypes": self.financier_types,
        }


@dataclass
class ProductApplication:
    id: str
    name: str
    country: str
    buyer_types: list[str] = field(default_factory=list)
    why_relevant: str = ""
    procurement_triggers: list[str] = field(default_factory=list)
    search_terms: list[str] = field(default_factory=list)
    social_search_terms: list[str] = field(default_factory=list)
    qualification_signals: list[str] = field(default_factory=list)
    bad_fit_signals: list[str] = field(default_factory=list)
    decision_makers: list[str] = field(default_factory=list)
    priority_score: float = 0.5
    confidence: float = 0.5
    source_type: str = "discovered"
    evidence: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ProductApplication":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", "Unknown Application"),
            country=d.get("country", ""),
            buyer_types=d.get("buyerTypes", []),
            why_relevant=d.get("whyRelevant", ""),
            procurement_triggers=d.get("procurementTriggers", []),
            search_terms=d.get("searchTerms", []),
            social_search_terms=d.get("socialSearchTerms", []),
            qualification_signals=d.get("qualificationSignals", []),
            bad_fit_signals=d.get("badFitSignals", []),
            decision_makers=d.get("decisionMakers", []),
            priority_score=d.get("priorityScore", 0.5),
            confidence=d.get("confidence", 0.5),
            source_type=d.get("sourceType", "discovered"),
            evidence=d.get("evidence", []),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "buyerTypes": self.buyer_types,
            "whyRelevant": self.why_relevant,
            "procurementTriggers": self.procurement_triggers,
            "searchTerms": self.search_terms,
            "socialSearchTerms": self.social_search_terms,
            "qualificationSignals": self.qualification_signals,
            "badFitSignals": self.bad_fit_signals,
            "decisionMakers": self.decision_makers,
            "priorityScore": self.priority_score,
            "confidence": self.confidence,
            "sourceType": self.source_type,
            "evidence": self.evidence,
        }


@dataclass
class CountryApplicationMap:
    product_name: str
    country: str
    product_role: ProductRole
    applications: list[ProductApplication] = field(default_factory=list)
    generated_at: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> "CountryApplicationMap":
        role_raw = d.get("productRole")
        role = ProductRole.from_dict(role_raw) if role_raw else ProductRole("machine or equipment")
        apps = [ProductApplication.from_dict(a) for a in (d.get("applications") or [])]
        return cls(
            product_name=d.get("productName", ""),
            country=d.get("country", ""),
            product_role=role,
            applications=apps,
            generated_at=d.get("generatedAt", 0.0),
        )

    def to_dict(self) -> dict:
        return {
            "productName": self.product_name,
            "country": self.country,
            "productRole": self.product_role.to_dict(),
            "applications": [a.to_dict() for a in self.applications],
            "generatedAt": self.generated_at,
        }


@dataclass
class LeadQualification:
    lead_id: str
    company_name: str
    result: str
    matched_signals: list[str] = field(default_factory=list)
    triggered_bad_fit_signals: list[str] = field(default_factory=list)
    reasoning: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "LeadQualification":
        return cls(
            lead_id=d.get("leadId", ""),
            company_name=d.get("companyName", ""),
            result=d.get("result", "uncertain"),
            matched_signals=d.get("matchedSignals", []),
            triggered_bad_fit_signals=d.get("triggeredBadFitSignals", []),
            reasoning=d.get("reasoning", ""),
        )

    def to_dict(self) -> dict:
        return {
            "leadId": self.lead_id,
            "companyName": self.company_name,
            "result": self.result,
            "matchedSignals": self.matched_signals,
            "triggeredBadFitSignals": self.triggered_bad_fit_signals,
            "reasoning": self.reasoning,
        }


@dataclass
class LaneQualificationReport:
    application_id: str
    application_name: str
    total_discovered: int
    qualified: int
    rejected: int
    uncertain: int
    qualifications: list[LeadQualification] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "LaneQualificationReport":
        quals = [LeadQualification.from_dict(q) for q in (d.get("qualifications") or [])]
        return cls(
            application_id=d.get("applicationId", ""),
            application_name=d.get("applicationName", ""),
            total_discovered=d.get("totalDiscovered", 0),
            qualified=d.get("qualified", 0),
            rejected=d.get("rejected", 0),
            uncertain=d.get("uncertain", 0),
            qualifications=quals,
        )

    def to_dict(self) -> dict:
        return {
            "applicationId": self.application_id,
            "applicationName": self.application_name,
            "totalDiscovered": self.total_discovered,
            "qualified": self.qualified,
            "rejected": self.rejected,
            "uncertain": self.uncertain,
            "qualifications": [q.to_dict() for q in self.qualifications],
        }


@dataclass
class ProductDetails:
    name: str
    description: Optional[str] = None
    target_region: Optional[str] = None
    price_point: Optional[str] = None
    target_company_size: Optional[str] = None
    target_lead_count: Optional[int] = 20
    target_audience: Optional[TargetAudienceType] = None
    supplier_country: Optional[str] = "China"
    assets: list[ProductAsset] = field(default_factory=list)
    strategic_context: Optional[StrategicContext] = None
    product_role: Optional[ProductRole] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "targetRegion": self.target_region,
            "pricePoint": self.price_point,
            "targetCompanySize": self.target_company_size,
            "targetLeadCount": self.target_lead_count,
            "targetAudience": self.target_audience,
            "supplierCountry": self.supplier_country,
            "strategicContext": self.strategic_context.to_dict() if self.strategic_context else None,
            "productRole": self.product_role.to_dict() if self.product_role else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProductDetails":
        ctx = d.get("strategicContext")
        role_raw = d.get("productRole")
        product_role = ProductRole.from_dict(role_raw) if role_raw else None
        return cls(
            name=d["name"],
            description=d.get("description"),
            target_region=d.get("targetRegion"),
            price_point=d.get("pricePoint"),
            target_company_size=d.get("targetCompanySize"),
            target_lead_count=d.get("targetLeadCount", 20),
            target_audience=d.get("targetAudience"),
            supplier_country=d.get("supplierCountry", "China"),
            strategic_context=StrategicContext.from_dict(ctx) if ctx else None,
            product_role=product_role,
        )


# ---------------------------------------------------------------------------
# Market Intelligence
# ---------------------------------------------------------------------------

@dataclass
class StatPoint:
    label: str
    value: float


@dataclass
class MarketStats:
    competitor_share: list[StatPoint] = field(default_factory=list)
    growth_trend: list[StatPoint] = field(default_factory=list)
    user_segments: list[StatPoint] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "MarketStats":
        def _to_float(v) -> float:
            if isinstance(v, (int, float)):
                return float(v)
            try:
                import re
                num = re.sub(r"[^\d.]", "", str(v))
                return float(num) if num else 0.0
            except (ValueError, TypeError):
                return 0.0

        def parse_points(lst: list) -> list[StatPoint]:
            return [StatPoint(label=p.get("label", ""), value=_to_float(p.get("value", 0))) for p in lst]
        return cls(
            competitor_share=parse_points(d.get("competitorShare", [])),
            growth_trend=parse_points(d.get("growthTrend", [])),
            user_segments=parse_points(d.get("userSegments", [])),
        )


@dataclass
class MarketReportSource:
    title: str
    url: str


@dataclass
class MarketReport:
    region: str
    overview: str
    market_size: str = "N/A"
    buying_habits: str = "N/A"
    competitors: list[str] = field(default_factory=list)
    regulations: str = "N/A"
    entry_strategy: str = "N/A"
    hs_code: str = "N/A"
    import_duty: str = "N/A"
    shipping_time: str = "N/A"
    price_structure: str = "N/A"
    trade_shows: list[str] = field(default_factory=list)
    localization: str = "N/A"
    sources: list[MarketReportSource] = field(default_factory=list)
    stats: Optional[MarketStats] = None

    def to_dict(self) -> dict:
        return {
            "region": self.region,
            "overview": self.overview,
            "marketSize": self.market_size,
            "buyingHabits": self.buying_habits,
            "competitors": self.competitors,
            "regulations": self.regulations,
            "entryStrategy": self.entry_strategy,
            "hsCode": self.hs_code,
            "importDuty": self.import_duty,
            "shippingTime": self.shipping_time,
            "priceStructure": self.price_structure,
            "tradeShows": self.trade_shows,
            "localization": self.localization,
        }


@dataclass
class RegionSuggestion:
    region: str
    reason: str
    demand_level: str  # 'High' | 'Medium' | 'Low'
    report: Optional[MarketReport] = None


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@dataclass
class SearchSession:
    """Top-level container for a market search session."""
    id: str
    name: str = "Unnamed"
    created_at: float = 0.0
    product: Optional[ProductDetails] = None
    strategic_context: Optional[StrategicContext] = None
    suggestions: list[RegionSuggestion] = field(default_factory=list)
    leads: list[Lead] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

class LeadStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    CONTACTING = "CONTACTING"
    NEGOTIATING = "NEGOTIATING"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


@dataclass
class MatchDetails:
    industry_fit: str = ""
    size_fit: str = ""
    location_fit: str = ""


@dataclass
class SocialProfile:
    platform: str
    url: str


@dataclass
class Competitor:
    name: str
    strengths: str = ""
    weaknesses: str = ""
    displacement_strategy: str = ""


@dataclass
class InteractionLog:
    timestamp: str
    actor: str   # 'AGENT' | 'CLIENT' | 'SYSTEM'
    message: str
    tactic: Optional[str] = None


@dataclass
class Lead:
    id: str
    company_name: str
    region: str
    status: LeadStatus
    confidence_score: int
    logs: list[InteractionLog] = field(default_factory=list)
    website: Optional[str] = None
    match_details: Optional[MatchDetails] = None
    summary: Optional[str] = None
    social_profiles: list[SocialProfile] = field(default_factory=list)
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
    competitors: list[Competitor] = field(default_factory=list)
    verification_status: Optional[str] = None
    verification_notes: Optional[str] = None
    sources: list[str] = field(default_factory=list)
    chat_history: list["ChatMessage"] = field(default_factory=list)

    # Agent pipeline fields
    evidence: list = field(default_factory=list)
    social_discovery: list = field(default_factory=list)
    verification: Optional[dict] = None
    score_breakdown: Optional[dict] = None
    recommendations: list = field(default_factory=list)
    outreach_drafts: list = field(default_factory=list)
    last_agent_action: Optional[str] = None

    # Application context tagging
    application_id: Optional[str] = None
    application: Optional[str] = None
    buyer_type: Optional[str] = None
    search_lane: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "companyName": self.company_name,
            "region": self.region,
            "status": self.status.value,
            "confidenceScore": self.confidence_score,
            "website": self.website,
            "summary": self.summary,
            "contactEmail": self.contact_email,
            "phoneNumber": self.phone_number,
            "address": self.address,
            "sourceUrl": self.source_url,
            "googleMapsUrl": self.google_maps_url,
            "searchVector": self.search_vector,
            "verificationStatus": self.verification_status,
            "verificationNotes": self.verification_notes,
            "sources": self.sources,
            "applicationId": self.application_id,
            "application": self.application,
            "buyerType": self.buyer_type,
            "searchLane": self.search_lane,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Lead":
        from tradenexus.models import Competitor, InteractionLog, MatchDetails, SocialProfile, ChatMessage
        
        def _get_val(keys: list[str], default=None):
            for k in keys:
                if k in d:
                    return d[k]
            return default

        logs_raw = _get_val(["logs"], [])
        logs = [InteractionLog(**log) if isinstance(log, dict) else log for log in logs_raw]

        md_raw = _get_val(["matchDetails", "match_details"])
        md = MatchDetails(**md_raw) if isinstance(md_raw, dict) else md_raw

        sp_raw = _get_val(["socialProfiles", "social_profiles"], [])
        sp = [SocialProfile(**profile) if isinstance(profile, dict) else profile for profile in sp_raw]

        comp_raw = _get_val(["competitors"], [])
        comp = [Competitor(**c) if isinstance(c, dict) else c for c in comp_raw]

        chat_raw = _get_val(["chatHistory", "chat_history"], [])
        chat = [ChatMessage(**msg) if isinstance(msg, dict) else msg for msg in chat_raw]

        return cls(
            id=d.get("id", ""),
            company_name=_get_val(["companyName", "company_name"], "Unknown Company"),
            region=d.get("region", ""),
            status=LeadStatus(_get_val(["status"], "DISCOVERED")),
            confidence_score=int(_get_val(["confidenceScore", "confidence_score"], 0)),
            logs=logs,
            website=d.get("website"),
            match_details=md,
            summary=d.get("summary"),
            social_profiles=sp,
            employee_count=_get_val(["employeeCount", "employee_count"]),
            revenue=d.get("revenue"),
            contact_email=_get_val(["contactEmail", "contact_email"]),
            phone_number=_get_val(["phoneNumber", "phone_number"]),
            address=d.get("address"),
            source_url=_get_val(["sourceUrl", "source_url"]),
            google_maps_url=_get_val(["googleMapsUrl", "google_maps_url"]),
            search_vector=_get_val(["searchVector", "search_vector"]),
            trade_volume=_get_val(["tradeVolume", "trade_volume"]),
            manufacturing_volume=_get_val(["manufacturingVolume", "manufacturing_volume"]),
            next_steps=_get_val(["nextSteps", "next_steps"]),
            competitors=comp,
            verification_status=_get_val(["verificationStatus", "verification_status"]),
            verification_notes=_get_val(["verificationNotes", "verification_notes"]),
            sources=d.get("sources", []),
            chat_history=chat,
            evidence=d.get("evidence", []),
            social_discovery=_get_val(["socialDiscovery", "social_discovery"], []),
            verification=d.get("verification"),
            score_breakdown=_get_val(["scoreBreakdown", "score_breakdown"]),
            recommendations=d.get("recommendations", []),
            outreach_drafts=_get_val(["outreachDrafts", "outreach_drafts"], []),
            last_agent_action=_get_val(["lastAgentAction", "last_agent_action"]),
            application_id=_get_val(["applicationId", "application_id"]),
            application=d.get("application"),
            buyer_type=_get_val(["buyerType", "buyer_type"]),
            search_lane=_get_val(["searchLane", "search_lane"]),
        )


@dataclass
class ChatMessage:
    role: str   # 'user' | 'model'
    content: str
    timestamp: float = 0.0
