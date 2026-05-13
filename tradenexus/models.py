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
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProductDetails":
        ctx = d.get("strategicContext")
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
        def parse_points(lst: list) -> list[StatPoint]:
            return [StatPoint(label=p.get("label", ""), value=float(p.get("value", 0))) for p in lst]
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
        }


@dataclass
class ChatMessage:
    role: str   # 'user' | 'model'
    content: str
    timestamp: float = 0.0
