"""
tradenexus/agent/types.py

Agent pipeline dataclasses — port of types/evidenceTypes.ts and types/agentTypes.ts.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Evidence types (evidenceTypes.ts)
# ---------------------------------------------------------------------------

@dataclass
class DiscoveryEvidence:
    id: str
    source_type: str  # 'web' | 'maps' | 'linkedin' | 'facebook' | etc.
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    extracted_fields: dict = field(default_factory=dict)
    confidence: float = 0.5
    found_at: float = 0.0
    found_by: str = ""
    validation_status: str = "UNVERIFIED"  # 'UNVERIFIED' | 'VALID' | 'CONFLICTING' | 'STALE' | 'REJECTED'


@dataclass
class SocialProfileEvidence:
    id: str
    source_type: str = "other"
    url: str = ""
    title: Optional[str] = None
    snippet: Optional[str] = None
    extracted_fields: dict = field(default_factory=dict)
    confidence: float = 0.5
    found_at: float = 0.0
    found_by: str = "socialDiscovery"
    validation_status: str = "UNVERIFIED"
    platform: str = "other"  # 'linkedin' | 'facebook' | 'instagram' | 'youtube' | 'tiktok' | 'x' | 'other'
    handle: Optional[str] = None
    is_official_likely: bool = False
    profile_type: str = "unknown"  # 'company' | 'employee' | 'founder' | 'reseller' | 'community' | 'unknown'
    activity_level: str = "UNKNOWN"  # 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN'
    activity_evidence: Optional[str] = None
    contact_hints: list[str] = field(default_factory=list)
    relevance_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Verification types (evidenceTypes.ts)
# ---------------------------------------------------------------------------

@dataclass
class VerificationCheck:
    id: str
    type: str  # 'LOCATION' | 'WEBSITE' | 'PRODUCT_FIT' | 'SOCIAL_OWNERSHIP' | 'CONTACT' | 'DUPLICATE' | 'COUNTRY_EXCLUSION'
    status: str = "UNKNOWN"  # 'PASS' | 'FAIL' | 'WARNING' | 'UNKNOWN'
    confidence: float = 0.5
    notes: str = ""
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class LeadVerification:
    status: str = "UNVERIFIED"  # 'VERIFIED' | 'PARTIAL' | 'FAILED' | 'UNVERIFIED'
    confidence: float = 0.0
    checks: list[VerificationCheck] = field(default_factory=list)
    updated_at: float = 0.0


# ---------------------------------------------------------------------------
# Scoring types (evidenceTypes.ts)
# ---------------------------------------------------------------------------

@dataclass
class LeadScoreBreakdown:
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


# ---------------------------------------------------------------------------
# Agent plan types (agentTypes.ts)
# ---------------------------------------------------------------------------

@dataclass
class AgentPlanStep:
    state: str  # 'ANALYZE_CONTEXT' | 'DISCOVER_MARKETS' | 'DISCOVER_LEADS' | etc.
    label: str
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = "PENDING"  # 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
    result: Optional[str] = None


@dataclass
class AgentPlan:
    id: str
    campaign_id: str
    steps: list[AgentPlanStep] = field(default_factory=list)
    current_step: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0


# ---------------------------------------------------------------------------
# Recommendation types (agentTypes.ts)
# ---------------------------------------------------------------------------

@dataclass
class AgentRecommendation:
    id: str
    type: str  # 'VERIFY' | 'ENRICH' | 'DRAFT_OUTREACH' | 'PRIORITIZE' | 'REJECT' | 'USER_REVIEW' | 'EXPORT'
    priority: str = "MEDIUM"  # 'HIGH' | 'MEDIUM' | 'LOW'
    title: str = ""
    reason: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    created_at: float = 0.0


# ---------------------------------------------------------------------------
# Outreach types (agentTypes.ts)
# ---------------------------------------------------------------------------

@dataclass
class OutreachDraft:
    id: str
    type: str  # 'cold_email' | 'linkedin_connection' | 'linkedin_followup' | 'whatsapp_short' | 'tradeshow_intro' | 'distributor_pitch'
    body: str
    subject: Optional[str] = None
    evidence_ids: list[str] = field(default_factory=list)
    created_at: float = 0.0
    approved: bool = False


# ---------------------------------------------------------------------------
# Closing strategy (closingStrategy.ts)
# ---------------------------------------------------------------------------

@dataclass
class ClosingStrategy:
    type: str  # 'DIRECT_VALUE_PITCH' | 'COMPETITIVE_DISPLACEMENT' | 'EDUCATIONAL_HOOK' | 'PROBLEM_SOLUTION' | 'PARTNERSHIP_APPROACH' | 'CASE_STUDY_APPROACH'
    rationale: str = ""
    key_talking_points: list[str] = field(default_factory=list)
    evidence_to_highlight: list[str] = field(default_factory=list)
    recommended_platform: str = "cold_email"
    confidence: int = 70
    generated_at: float = 0.0


# ---------------------------------------------------------------------------
# Follow-up sequence types (followUpPlanning.ts)
# ---------------------------------------------------------------------------

@dataclass
class OutreachSequenceStep:
    step: int
    type: str
    timing: str
    goal: str
    draft_id: Optional[str] = None


@dataclass
class OutreachSequence:
    id: str
    lead_id: str
    strategy_type: str
    steps: list[OutreachSequenceStep] = field(default_factory=list)
    total_days: int = 14
    rationale: str = ""
    generated_at: float = 0.0


# ---------------------------------------------------------------------------
# Memory types (agentTypes.ts)
# ---------------------------------------------------------------------------

@dataclass
class MemoryEvent:
    id: str
    type: str  # 'LEAD_ACCEPTED' | 'LEAD_REJECTED' | 'LEAD_STATUS_CHANGED' | etc.
    lead_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class CampaignMemory:
    events: list[MemoryEvent] = field(default_factory=list)
    preferred_lead_patterns: list[str] = field(default_factory=list)
    rejected_lead_patterns: list[str] = field(default_factory=list)
    strong_regions: list[str] = field(default_factory=list)
    weak_regions: list[str] = field(default_factory=list)
    platform_usefulness: dict[str, int] = field(default_factory=dict)
    buyer_type_performance: dict[str, int] = field(default_factory=dict)
    updated_at: float = 0.0
