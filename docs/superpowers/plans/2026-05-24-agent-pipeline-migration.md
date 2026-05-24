# Agent Pipeline Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port all 18 Express agent pipeline modules to Python and split the 618-line `gemini_service.py` into focused `core/` modules.

**Architecture:** Shared utility imports (no base class), absolute imports only (`from tradenexus.config import ...`), pure-logic modules have zero AI dependencies, AI-call modules use `genai.Client` directly.

**Tech Stack:** Python 3.11+, google-genai, typer, rich, python-dotenv

---

### Task 1: Create directory structure and `__init__.py` files

**Files:**
- Create: `tradenexus/core/__init__.py`
- Create: `tradenexus/agent/__init__.py`
- Create: `tradenexus/agent/discovery/__init__.py`
- Create: `tradenexus/agent/enrichment/__init__.py`
- Create: `tradenexus/agent/verification/__init__.py`
- Create: `tradenexus/agent/scoring/__init__.py`
- Create: `tradenexus/agent/planner/__init__.py`
- Create: `tradenexus/agent/memory/__init__.py`
- Create: `tradenexus/agent/outreach/__init__.py`

- [ ] **Step 1: Create all directories and `__init__.py` files**

```bash
mkdir -p tradenexus/core
mkdir -p tradenexus/agent/discovery
mkdir -p tradenexus/agent/enrichment
mkdir -p tradenexus/agent/verification
mkdir -p tradenexus/agent/scoring
mkdir -p tradenexus/agent/planner
mkdir -p tradenexus/agent/memory
mkdir -p tradenexus/agent/outreach
touch tradenexus/core/__init__.py
touch tradenexus/agent/__init__.py
touch tradenexus/agent/discovery/__init__.py
touch tradenexus/agent/enrichment/__init__.py
touch tradenexus/agent/verification/__init__.py
touch tradenexus/agent/scoring/__init__.py
touch tradenexus/agent/planner/__init__.py
touch tradenexus/agent/memory/__init__.py
touch tradenexus/agent/outreach/__init__.py
```

- [ ] **Step 2: Verify directories exist**

```bash
find tradenexus/core tradenexus/agent -type f | sort
```

Expected: 10 `__init__.py` files listed.

- [ ] **Step 3: Commit**

```bash
git add tradenexus/core/ tradenexus/agent/
git commit -m "chore: create core/ and agent/ package directories

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Add agent pipeline types

**Files:**
- Create: `tradenexus/agent/types.py`
- Modify: `tradenexus/models.py` — add new fields to `Lead` dataclass

- [ ] **Step 1: Write `tradenexus/agent/types.py`**

```python
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
```

- [ ] **Step 2: Extend `Lead` in `tradenexus/models.py`**

Add these fields to the `Lead` dataclass (append after existing `chat_history` field at line 246):

```python
    # Agent pipeline fields (Phase 1-6)
    evidence: list = field(default_factory=list)  # DiscoveryEvidence[]
    social_discovery: list = field(default_factory=list)  # SocialProfileEvidence[]
    verification: Optional[dict] = None  # LeadVerification (stored as dict for simplicity)
    score_breakdown: Optional[dict] = None  # LeadScoreBreakdown (stored as dict)
    recommendations: list = field(default_factory=list)  # AgentRecommendation[]
    outreach_drafts: list = field(default_factory=list)  # OutreachDraft[]
    last_agent_action: Optional[str] = None
```

Use the Edit tool to insert after the `chat_history` line:
```python
    chat_history: list["ChatMessage"] = field(default_factory=list)
```

Insert after it:
```python
    # Agent pipeline fields
    evidence: list = field(default_factory=list)
    social_discovery: list = field(default_factory=list)
    verification: Optional[dict] = None
    score_breakdown: Optional[dict] = None
    recommendations: list = field(default_factory=list)
    outreach_drafts: list = field(default_factory=list)
    last_agent_action: Optional[str] = None
```

- [ ] **Step 3: Verify Python can import the new types**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "from tradenexus.agent.types import LeadVerification, LeadScoreBreakdown, ClosingStrategy, OutreachDraft, CampaignMemory; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tradenexus/agent/types.py tradenexus/models.py
git commit -m "feat: add agent pipeline dataclasses and extend Lead model

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Split gemini_service.py — extract `tradenexus/core/context.py`

**Files:**
- Create: `tradenexus/core/context.py`
- Modify: `tradenexus/gemini_service.py` — remove the extracted function

- [ ] **Step 1: Write `tradenexus/core/context.py`**

Copy `extract_search_strategy_from_assets()` and `FALLBACK_CONTEXT` from `gemini_service.py:34-95` into this new file:

```python
"""
tradenexus/core/context.py

Extract strategic context from product documents (PDFs/images).
Port of extractSearchStrategyFromAssets().
"""

from __future__ import annotations
import json
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import ProductDetails, ProductAsset, StrategicContext


FALLBACK_CONTEXT = StrategicContext()


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def extract_search_strategy_from_assets(product: ProductDetails) -> StrategicContext:
    """Analyse product files (PDFs/images) and extract a StrategicContext."""
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
```

- [ ] **Step 2: Verify context module works standalone**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "from tradenexus.core.context import extract_search_strategy_from_assets; print('import OK')"
```

Expected: `import OK`

- [ ] **Step 3: Commit**

```bash
git add tradenexus/core/context.py
git commit -m "refactor: extract context module from gemini_service.py

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Split gemini_service.py — extract `tradenexus/core/markets.py`

**Files:**
- Create: `tradenexus/core/markets.py`

- [ ] **Step 1: Write `tradenexus/core/markets.py`**

Copy `analyze_markets()` and `generate_market_report()` from `gemini_service.py:102-255` into this new file:

```python
"""
tradenexus/core/markets.py

Market analysis and intelligence reports.
Port of analyzeMarkets() and generateMarketReport().
"""

from __future__ import annotations
import json
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import (
    MarketReport, MarketReportSource, MarketStats,
    ProductAsset, ProductDetails, RegionSuggestion, StrategicContext,
)
from tradenexus.utils import extract_json_from_text, extract_grounding_sources


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


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
    """Find the top 9 export markets for a product."""
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
    """Generate a full market intelligence report with Google Search grounding."""
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
```

- [ ] **Step 2: Verify markets module imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "from tradenexus.core.markets import analyze_markets, generate_market_report; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tradenexus/core/markets.py
git commit -m "refactor: extract markets module from gemini_service.py

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Split gemini_service.py — extract `tradenexus/core/leads.py`

**Files:**
- Create: `tradenexus/core/leads.py`

- [ ] **Step 1: Write `tradenexus/core/leads.py`**

Copy `verify_lead()`, `_identify_strategic_hubs()`, `_execute_lead_batch()`, `_run_search_vector()`, and `search_for_leads()` from `gemini_service.py:262-551` into this new file:

```python
"""
tradenexus/core/leads.py

Lead discovery and verification.
Port of searchForLeads(), verifyLead(), and internal helpers.
"""

from __future__ import annotations
import asyncio
import uuid
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import (
    ChatMessage, Competitor, InteractionLog, Lead, LeadStatus,
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
    """Verify a lead's legitimacy via Google Search + Maps. Returns partial Lead update dict."""
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
    """Identify up to 12 strategic hubs (cities/countries) for the target region."""
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


import json  # needed for _identify_strategic_hubs


def _execute_lead_batch(
    product: ProductDetails,
    vector_name: str,
    vector_prompt: str,
    target_count: int,
    context: Optional[StrategicContext] = None,
) -> list[dict]:
    """Single AI call for one batch of leads in a territory."""
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
    """Run one search vector, splitting into batches of 8 to avoid token limits."""
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
    """Run the multi-vector 4-squad lead discovery engine."""
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
```

- [ ] **Step 2: Verify leads module imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "from tradenexus.core.leads import search_for_leads, verify_lead; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tradenexus/core/leads.py
git commit -m "refactor: extract leads module from gemini_service.py

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Split gemini_service.py — extract `tradenexus/core/prospecting.py`

**Files:**
- Create: `tradenexus/core/prospecting.py`

- [ ] **Step 1: Write `tradenexus/core/prospecting.py`**

Copy `generate_prospecting_message()` from `gemini_service.py:558-618`:

```python
"""
tradenexus/core/prospecting.py

SDR prospecting chat assistant.
Port of generateProspectingMessage().
"""

from __future__ import annotations
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, GROUNDING_MODEL, build_thinking_config
from tradenexus.models import ChatMessage, Lead, StrategicContext
from tradenexus.utils import extract_grounding_sources


FALLBACK_CONTEXT = StrategicContext()


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def generate_prospecting_message(
    history: list[ChatMessage],
    lead: Lead,
    product_context: Optional[StrategicContext] = None,
) -> str:
    """SDR assistant — chat about a specific lead and draft outreach messages."""
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
```

- [ ] **Step 2: Verify prospecting module imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "from tradenexus.core.prospecting import generate_prospecting_message; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tradenexus/core/prospecting.py
git commit -m "refactor: extract prospecting module from gemini_service.py

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Update `main.py` imports to use `core/` modules

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update imports in `main.py`**

Change the import block (around line 34-38) from:

```python
from tradenexus.config import DEFAULT_MODEL, GROUNDING_MODEL, THINKING_BUDGET
from tradenexus.models import ChatMessage, ProductDetails, ProductAsset, StrategicContext
from tradenexus import gemini_service as gs
from tradenexus import session as sess
from tradenexus import output as out
```

To:

```python
from tradenexus.config import DEFAULT_MODEL, GROUNDING_MODEL, THINKING_BUDGET
from tradenexus.models import ChatMessage, ProductDetails, ProductAsset, StrategicContext
from tradenexus.core.context import extract_search_strategy_from_assets
from tradenexus.core.markets import analyze_markets, generate_market_report
from tradenexus.core.leads import search_for_leads, verify_lead
from tradenexus.core.prospecting import generate_prospecting_message
from tradenexus import session as sess
from tradenexus import output as out
```

- [ ] **Step 2: Replace all `gs.` calls in `main.py`**

- `gs.analyze_markets(...)` → `analyze_markets(...)`  (line ~117)
- `gs.generate_market_report(...)` → `generate_market_report(...)`  (line ~153)
- `gs.search_for_leads(...)` → `search_for_leads(...)`  (line ~185)
- `gs.verify_lead(...)` → `verify_lead(...)`  (line ~246)
- `gs.generate_prospecting_message(...)` → `generate_prospecting_message(...)`  (line ~306)
- `gs.extract_search_strategy_from_assets(...)` → `extract_search_strategy_from_assets(...)`  (line ~347)

- [ ] **Step 3: Verify CLI still works**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python main.py info
```

Expected: Shows API key status and config (same as before).

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: update main.py imports to use core/ modules

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Delete `gemini_service.py` and verify nothing is broken

**Files:**
- Delete: `tradenexus/gemini_service.py`

- [ ] **Step 1: Delete the old file**

```bash
rm tradenexus/gemini_service.py
```

- [ ] **Step 2: Verify nothing imports from it anymore**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && grep -r "gemini_service" --include="*.py" . || echo "No references found"
```

Expected: `No references found`

- [ ] **Step 3: Verify full import chain works**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.core.context import extract_search_strategy_from_assets
from tradenexus.core.markets import analyze_markets, generate_market_report
from tradenexus.core.leads import search_for_leads, verify_lead
from tradenexus.core.prospecting import generate_prospecting_message
from tradenexus.models import Lead, ProductDetails, StrategicContext
from tradenexus.agent.types import LeadVerification, ClosingStrategy, CampaignMemory
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 4: Commit**

```bash
git rm tradenexus/gemini_service.py
git commit -m "refactor: remove gemini_service.py, replaced by core/ modules

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Port social discovery agent (`tradenexus/agent/discovery/social.py`)

**Files:**
- Create: `tradenexus/agent/discovery/social.py`

- [ ] **Step 1: Write `tradenexus/agent/discovery/social.py`**

Port of `server/agent/discovery/socialDiscovery.ts`:

```python
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
```

- [ ] **Step 2: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "from tradenexus.agent.discovery.social import discover_social_for_company, discover_leads_from_social; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tradenexus/agent/discovery/social.py
git commit -m "feat: port social discovery agent to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: Port social-to-lead converter (`tradenexus/agent/discovery/social_to_lead.py`)

**Files:**
- Create: `tradenexus/agent/discovery/social_to_lead.py`

- [ ] **Step 1: Write the pure-logic module**

Port of `server/agent/discovery/socialToLead.ts`:

```python
"""
tradenexus/agent/discovery/social_to_lead.py

Phase 3 — Convert SocialProfileEvidence[] to Lead[] objects.
Port of server/agent/discovery/socialToLead.ts (pure logic, no AI).
"""

from __future__ import annotations
import uuid
import time

from tradenexus.models import Lead, LeadStatus, InteractionLog, SocialProfile
from tradenexus.agent.types import SocialProfileEvidence


SOCIAL_VECTOR_PREFIX = "Social:"


def social_profiles_to_leads(
    profiles: list[SocialProfileEvidence],
    region: str,
) -> list[Lead]:
    """Group social profiles by company name and convert to Lead objects."""
    now = time.time()

    # Group profiles by company name to avoid duplicates
    by_company: dict[str, list[SocialProfileEvidence]] = {}
    for profile in profiles:
        name = (
            profile.extracted_fields.get("companyName")
            or profile.title
            or "Unknown Company"
        )
        key = name.lower().strip()
        if key not in by_company:
            by_company[key] = []
        by_company[key].append(profile)

    leads: list[Lead] = []
    for company_profiles in by_company.values():
        primary = company_profiles[0]
        company_name = (
            primary.extracted_fields.get("companyName")
            or primary.title
            or "Unknown Company"
        )
        website = primary.extracted_fields.get("website") or None

        # Collect unique platforms for the search vector
        platforms = list({p.platform for p in company_profiles})
        vector_name = f"{SOCIAL_VECTOR_PREFIX} {'/'.join(platforms)}"

        # Extract contact hints from all profiles
        all_contact_hints: list[str] = []
        for p in company_profiles:
            all_contact_hints.extend(p.contact_hints or [])
        contact_info = ", ".join(list(dict.fromkeys(all_contact_hints))) or None

        # Best confidence across all profiles
        best_confidence = max(p.confidence for p in company_profiles)

        # Best activity level across profiles
        activity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}
        best_activity = max(
            company_profiles,
            key=lambda p: activity_order.get(p.activity_level, 0),
        ).activity_level

        lead = Lead(
            id=str(uuid.uuid4()),
            company_name=str(company_name),
            website=str(website) if website else None,
            region=region,
            status=LeadStatus.DISCOVERED,
            confidence_score=round(best_confidence * 100),
            summary=primary.relevance_notes or primary.snippet,
            social_profiles=[
                SocialProfile(platform=p.platform, url=p.url)
                for p in company_profiles
            ],
            social_discovery=[p for p in company_profiles],
            search_vector=vector_name,
            employee_count=primary.extracted_fields.get("employeeCount") or None,
            last_agent_action="socialDiscovery",
            logs=[
                InteractionLog(
                    timestamp=time.strftime("%H:%M:%S", time.localtime(now)),
                    actor="SYSTEM",
                    message=(
                        f"Lead discovered via social media on {', '.join(platforms)}.\n"
                        f"Activity Level: {best_activity}\n"
                        f"Platforms found: {len(company_profiles)} profile(s)"
                    ),
                )
            ],
        )
        leads.append(lead)

    return leads
```

- [ ] **Step 2: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "from tradenexus.agent.discovery.social_to_lead import social_profiles_to_leads; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tradenexus/agent/discovery/social_to_lead.py
git commit -m "feat: port social-to-lead converter to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: Port maps/web discovery evidence extractors

**Files:**
- Create: `tradenexus/agent/discovery/maps.py`
- Create: `tradenexus/agent/discovery/web.py`
- Create: `tradenexus/agent/discovery/directory.py`

- [ ] **Step 1: Write `tradenexus/agent/discovery/maps.py`**

```python
"""
tradenexus/agent/discovery/maps.py

Phase 1 — Extract maps-related evidence from existing lead data.
Port of server/agent/discovery/mapsDiscovery.ts (pure logic).
"""

from __future__ import annotations
import uuid
import time

from tradenexus.models import Lead
from tradenexus.agent.types import DiscoveryEvidence


def extract_maps_evidence(lead: Lead) -> list[DiscoveryEvidence]:
    """Pull Google Maps evidence from a lead that already has googleMapsUrl."""
    evidence: list[DiscoveryEvidence] = []
    now = time.time()

    if lead.google_maps_url:
        evidence.append(
            DiscoveryEvidence(
                id=str(uuid.uuid4()),
                source_type="maps",
                url=lead.google_maps_url,
                title=lead.company_name,
                snippet=lead.address,
                confidence=0.9,
                found_at=now,
                found_by="mapsDiscovery",
                validation_status="UNVERIFIED",
                extracted_fields={
                    "companyName": lead.company_name,
                    "address": lead.address or "",
                    "region": lead.region,
                },
            )
        )

    return evidence
```

- [ ] **Step 2: Write `tradenexus/agent/discovery/web.py`**

```python
"""
tradenexus/agent/discovery/web.py

Phase 1 — Wraps existing search_for_leads and attaches DiscoveryEvidence to each lead.
Port of server/agent/discovery/webDiscovery.ts
"""

from __future__ import annotations
import uuid
import time

from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import DiscoveryEvidence
from tradenexus.core.leads import search_for_leads


def discover_leads_from_web(product: ProductDetails) -> list[Lead]:
    """Search for leads and attach structured evidence records to each."""
    leads = search_for_leads(product)
    now = time.time()

    enriched: list[Lead] = []
    for lead in leads:
        evidence_records: list[DiscoveryEvidence] = []

        # Wrap source URL as web evidence
        if lead.source_url:
            evidence_records.append(
                DiscoveryEvidence(
                    id=str(uuid.uuid4()),
                    source_type="web",
                    url=lead.source_url,
                    title=lead.company_name,
                    snippet=lead.summary,
                    confidence=lead.confidence_score / 100,
                    found_at=now,
                    found_by="webDiscovery",
                    validation_status="UNVERIFIED",
                    extracted_fields={
                        "companyName": lead.company_name,
                        "website": lead.website or "",
                        "region": lead.region,
                        "address": lead.address or "",
                    },
                )
            )

        # Wrap Google Maps URL as maps evidence
        if lead.google_maps_url:
            evidence_records.append(
                DiscoveryEvidence(
                    id=str(uuid.uuid4()),
                    source_type="maps",
                    url=lead.google_maps_url,
                    title=lead.company_name,
                    snippet=lead.address,
                    confidence=0.9,
                    found_at=now,
                    found_by="mapsDiscovery",
                    validation_status="UNVERIFIED",
                    extracted_fields={
                        "address": lead.address or "",
                        "companyName": lead.company_name,
                    },
                )
            )

        # Wrap sources array items as additional web evidence
        if lead.sources:
            for source_url in lead.sources:
                if source_url and source_url != lead.source_url:
                    evidence_records.append(
                        DiscoveryEvidence(
                            id=str(uuid.uuid4()),
                            source_type="web",
                            url=source_url,
                            confidence=0.7,
                            found_at=now,
                            found_by="webDiscovery",
                            validation_status="UNVERIFIED",
                        )
                    )

        lead.evidence = evidence_records
        lead.last_agent_action = "webDiscovery"
        enriched.append(lead)

    return enriched
```

- [ ] **Step 3: Write `tradenexus/agent/discovery/directory.py`** (stub — matches TS)

```python
"""
tradenexus/agent/discovery/directory.py

Phase 3+ — Directory discovery: searches business directories and company registries.
Port of server/agent/discovery/directoryDiscovery.ts (stub).
"""

from __future__ import annotations

from tradenexus.models import ProductDetails
from tradenexus.agent.types import DiscoveryEvidence


def discover_from_directories(product: ProductDetails) -> list[DiscoveryEvidence]:
    """Search business directories for leads. Not yet implemented."""
    raise NotImplementedError("Directory discovery not yet implemented (Phase 3+)")
```

- [ ] **Step 4: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.agent.discovery.maps import extract_maps_evidence
from tradenexus.agent.discovery.web import discover_leads_from_web
from tradenexus.agent.discovery.directory import discover_from_directories
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tradenexus/agent/discovery/maps.py tradenexus/agent/discovery/web.py tradenexus/agent/discovery/directory.py
git commit -m "feat: port maps, web, and directory discovery modules to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: Port enrichment modules (stubs)

**Files:**
- Create: `tradenexus/agent/enrichment/contact.py`
- Create: `tradenexus/agent/enrichment/social.py`
- Create: `tradenexus/agent/enrichment/website.py`

- [ ] **Step 1: Write all three enrichment stubs**

`tradenexus/agent/enrichment/contact.py`:
```python
"""
tradenexus/agent/enrichment/contact.py

Phase 4 — Contact enrichment: finds email/phone/contact details for leads.
Port of server/agent/enrichment/contactEnrichment.ts (stub).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from tradenexus.models import Lead


@dataclass
class ContactInfo:
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    source: str = ""
    confidence: float = 0.0


def enrich_contact_info(lead: Lead) -> list[ContactInfo]:
    """Find email/phone/contact details for a lead. Not yet implemented."""
    raise NotImplementedError("Contact enrichment not yet implemented (Phase 4)")
```

`tradenexus/agent/enrichment/social.py`:
```python
"""
tradenexus/agent/enrichment/social.py

Phase 2 — Social enrichment: enriches leads with social profile details.
Port of server/agent/enrichment/socialEnrichment.ts (stub).
"""

from __future__ import annotations

from tradenexus.models import Lead
from tradenexus.agent.types import SocialProfileEvidence


def enrich_social_profiles(lead: Lead) -> list[SocialProfileEvidence]:
    """Enrich a lead with social profile details. Not yet implemented."""
    raise NotImplementedError("Social enrichment not yet implemented (Phase 2)")
```

`tradenexus/agent/enrichment/website.py`:
```python
"""
tradenexus/agent/enrichment/website.py

Phase 4 — Website enrichment: extracts structured data from lead websites.
Port of server/agent/enrichment/websiteEnrichment.ts (stub).
"""

from __future__ import annotations

from tradenexus.models import Lead
from tradenexus.agent.types import DiscoveryEvidence


def enrich_from_website(lead: Lead) -> list[DiscoveryEvidence]:
    """Scrape and extract structured data from a lead's website. Not yet implemented."""
    raise NotImplementedError("Website enrichment not yet implemented (Phase 4)")
```

- [ ] **Step 2: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.agent.enrichment.contact import enrich_contact_info, ContactInfo
from tradenexus.agent.enrichment.social import enrich_social_profiles
from tradenexus.agent.enrichment.website import enrich_from_website
print('OK')
"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tradenexus/agent/enrichment/
git commit -m "feat: port enrichment modules to Python (stubs)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: Port lead verification agent (`tradenexus/agent/verification/lead.py`)

**Files:**
- Create: `tradenexus/agent/verification/lead.py`
- Create: `tradenexus/agent/verification/evidence.py` (stub)
- Create: `tradenexus/agent/verification/social.py` (stub)

- [ ] **Step 1: Write `tradenexus/agent/verification/lead.py`**

Port of `server/agent/verification/leadVerification.ts`:

```python
"""
tradenexus/agent/verification/lead.py

Phase 4 — Multi-check lead verification that cross-references evidence.
Port of server/agent/verification/leadVerification.ts
"""

from __future__ import annotations
import uuid
import time
import json
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import LeadVerification, VerificationCheck
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def verify_lead(
    lead: Lead,
    product: Optional[ProductDetails] = None,
) -> LeadVerification:
    """Run 6 verification checks (LOCATION, WEBSITE, PRODUCT_FIT, SOCIAL_OWNERSHIP, CONTACT, DUPLICATE)."""
    now = time.time()

    product_name = product.name if product else "the product"

    evidence_list = ""
    if lead.evidence:
        evidence_list = "\n".join(
            f"- {e.get('sourceType', e.source_type if hasattr(e, 'source_type') else '?')}: "
            f"{e.get('url', e.url if hasattr(e, 'url') else '?')} "
            f"(confidence: {e.get('confidence', e.confidence if hasattr(e, 'confidence') else 0)})"
            for e in (lead.evidence if isinstance(lead.evidence, list) else [])
        ) if lead.evidence else ""
    if not evidence_list:
        evidence_list = "No evidence available."

    social_profiles_str = ""
    if lead.social_discovery:
        sp_list = lead.social_discovery if isinstance(lead.social_discovery, list) else []
        social_profiles_str = "\n".join(
            f"- {s.get('platform', s.platform if hasattr(s, 'platform') else '?')}: "
            f"{s.get('url', s.url if hasattr(s, 'url') else '?')} "
            f"(official: {s.get('isOfficialLikely', s.is_official_likely if hasattr(s, 'is_official_likely') else False)})"
            for s in sp_list
        ) if sp_list else ""
    if not social_profiles_str:
        social_profiles_str = "No social profiles discovered."

    prompt = f"""
You are a Lead Verification Specialist. Verify the legitimacy of a sales lead using available evidence.

LEAD: "{lead.company_name}"
REGION: {lead.region}
WEBSITE: {lead.website or 'Unknown'}
ADDRESS: {lead.address or 'Unknown'}
CONFIDENCE SCORE: {lead.confidence_score}/100
GOOGLE MAPS URL: {lead.google_maps_url or 'Not available'}

PRODUCT WE ARE SELLING: {product_name}

EVIDENCE RECORDS:
{evidence_list}

SOCIAL PROFILES:
{social_profiles_str}

TASK: Run these verification checks and return a JSON object:

1. LOCATION — Does the company physically exist in {lead.region}? Check Google Maps data, address validity.
2. WEBSITE — Is the website active and relevant to their claimed business?
3. PRODUCT_FIT — Does this company potentially buy, distribute, or use {product_name}?
4. SOCIAL_OWNERSHIP — Do the social profiles genuinely belong to this company?
5. CONTACT — Is there usable contact information available?
6. DUPLICATE — Any sign this is a duplicate of another known lead? (usually PASS unless evidence suggests duplication)

For EACH check, return: type, status (PASS|FAIL|WARNING|UNKNOWN), confidence (0-1), notes, evidenceIds (empty array).

OVERALL:
- status: "VERIFIED" (all critical pass), "PARTIAL" (most pass but some warnings), "FAILED" (critical fail), or "UNVERIFIED" (insufficient data)
- confidence: 0-1

Return ONLY a JSON object with "checks" array and "status"/"confidence" fields. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
                tools=[gtypes.Tool(google_search=gtypes.GoogleSearch())],
            ),
        )

        if not response.text:
            return LeadVerification(
                status="UNVERIFIED",
                confidence=0,
                checks=[
                    VerificationCheck(
                        id=str(uuid.uuid4()),
                        type="LOCATION",
                        status="UNKNOWN",
                        confidence=0,
                        notes="Verification failed: model returned empty response.",
                    )
                ],
                updated_at=now,
            )

        parsed = extract_json_from_text(response.text)
        if not parsed:
            return LeadVerification(
                status="UNVERIFIED",
                confidence=0,
                checks=[
                    VerificationCheck(
                        id=str(uuid.uuid4()),
                        type="LOCATION",
                        status="UNKNOWN",
                        confidence=0,
                        notes="Verification failed: could not parse model response.",
                    )
                ],
                updated_at=now,
            )

        parsed_checks = []
        for c in (parsed.get("checks") or []):
            parsed_checks.append(
                VerificationCheck(
                    id=str(uuid.uuid4()),
                    type=c.get("type", "LOCATION"),
                    status=c.get("status", "UNKNOWN"),
                    confidence=float(c.get("confidence", 0.5)),
                    notes=c.get("notes", ""),
                    evidence_ids=c.get("evidenceIds") if isinstance(c.get("evidenceIds"), list) else [],
                )
            )

        return LeadVerification(
            status=parsed.get("status", "UNVERIFIED"),
            confidence=float(parsed.get("confidence", 0)),
            checks=parsed_checks,
            updated_at=now,
        )

    except Exception as e:
        print(f"[LeadVerification] Error for {lead.company_name}: {e}")
        return LeadVerification(
            status="UNVERIFIED",
            confidence=0,
            checks=[
                VerificationCheck(
                    id=str(uuid.uuid4()),
                    type="LOCATION",
                    status="UNKNOWN",
                    confidence=0,
                    notes=f"Verification error: {e}",
                )
            ],
            updated_at=now,
        )
```

- [ ] **Step 2: Write stub `tradenexus/agent/verification/evidence.py`**

```python
"""
tradenexus/agent/verification/evidence.py

Phase 4 — Evidence validation: cross-references evidence for conflicts.
Port of server/agent/verification/evidenceValidation.ts (stub).
"""

from __future__ import annotations
from dataclasses import dataclass

from tradenexus.agent.types import DiscoveryEvidence


@dataclass
class EvidenceConflict:
    evidence_a: str
    evidence_b: str
    field: str
    description: str


def find_evidence_conflicts(evidence: list[DiscoveryEvidence]) -> list[EvidenceConflict]:
    """Cross-reference evidence records for conflicts. Not yet implemented."""
    raise NotImplementedError("Evidence validation not yet implemented (Phase 4)")
```

- [ ] **Step 3: Write stub `tradenexus/agent/verification/social.py`**

```python
"""
tradenexus/agent/verification/social.py

Phase 4 — Social profile verification: checks if social profiles genuinely belong to the company.
Port of server/agent/verification/socialProfileVerification.ts (stub).
"""

from __future__ import annotations

from tradenexus.agent.types import SocialProfileEvidence


def verify_social_profile(profile: SocialProfileEvidence) -> SocialProfileEvidence:
    """Verify a social profile's authenticity. Not yet implemented."""
    raise NotImplementedError("Social profile verification not yet implemented (Phase 4)")
```

- [ ] **Step 4: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.agent.verification.lead import verify_lead
from tradenexus.agent.verification.evidence import find_evidence_conflicts, EvidenceConflict
from tradenexus.agent.verification.social import verify_social_profile
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tradenexus/agent/verification/
git commit -m "feat: port lead verification agent and stubs to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: Port lead scoring modules

**Files:**
- Create: `tradenexus/agent/scoring/lead.py`
- Create: `tradenexus/agent/scoring/breakdown.py`

- [ ] **Step 1: Write `tradenexus/agent/scoring/lead.py`**

Port of `server/agent/scoring/leadScoring.ts`:

```python
"""
tradenexus/agent/scoring/lead.py

Phase 4 — AI-powered lead scoring with 10-dimensional breakdown.
Port of server/agent/scoring/leadScoring.ts
"""

from __future__ import annotations
import time
import json
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import LeadScoreBreakdown
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def _clamp_score(value) -> int:
    if isinstance(value, (int, float)):
        return max(0, min(100, round(value)))
    return 50


def score_lead(
    lead: Lead,
    product: Optional[ProductDetails] = None,
) -> LeadScoreBreakdown:
    """Score a lead across 10 dimensions using AI."""
    now = time.time()
    product_name = product.name if product else "the product"

    evidence_count = len(lead.evidence) if lead.evidence else 0
    social_count = len(lead.social_discovery) if lead.social_discovery else 0
    verification_status = lead.verification.get("status", "UNVERIFIED") if isinstance(lead.verification, dict) else "UNVERIFIED"

    prompt = f"""
You are a Lead Scoring Specialist. Score this lead across 10 dimensions based on available data.

LEAD: "{lead.company_name}"
REGION: {lead.region}
WEBSITE: {lead.website or 'None'}
CONFIDENCE: {lead.confidence_score}/100
EVIDENCE RECORDS: {evidence_count}
SOCIAL PROFILES: {social_count}
VERIFICATION STATUS: {verification_status}
EMPLOYEE COUNT: {lead.employee_count or 'Unknown'}
HAS CONTACT INFO: {'Yes' if (lead.contact_email or lead.phone_number) else 'No'}

PRODUCT: {product_name}

CONTEXT: {lead.summary or 'No summary available.'}

Score each dimension 0-100 (0 = worst, 100 = best):

1. locationFit — Is the lead in the right region?
2. productFit — Does this company need/could use {product_name}?
3. buyerTypeFit — Is this company the right buyer type?
4. companySizeFit — Is the company appropriately sized?
5. evidenceQuality — How good is the evidence?
6. socialActivity — How active is the company on social media?
7. contactability — Can we contact this company?
8. competitiveOpportunity — Is there a gap in the market? Are competitors weak?
9. freshness — How recently was this lead discovered?
10. overall — Weighted average, weighted toward productFit and evidenceQuality.

Also provide rationale: 2-3 sentences explaining the overall score.

Return ONLY a JSON object with numeric fields. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
            ),
        )

        if not response.text:
            return LeadScoreBreakdown(rationale="Model returned empty response", updated_at=now)

        parsed = extract_json_from_text(response.text)
        if not parsed:
            return LeadScoreBreakdown(rationale="Could not parse model response", updated_at=now)

        return LeadScoreBreakdown(
            overall=_clamp_score(parsed.get("overall")),
            location_fit=_clamp_score(parsed.get("locationFit")),
            product_fit=_clamp_score(parsed.get("productFit")),
            buyer_type_fit=_clamp_score(parsed.get("buyerTypeFit")),
            company_size_fit=_clamp_score(parsed.get("companySizeFit")),
            evidence_quality=_clamp_score(parsed.get("evidenceQuality")),
            social_activity=_clamp_score(parsed.get("socialActivity")),
            contactability=_clamp_score(parsed.get("contactability")),
            competitive_opportunity=_clamp_score(parsed.get("competitiveOpportunity")),
            freshness=_clamp_score(parsed.get("freshness")),
            rationale=parsed.get("rationale", "Score generated from available data."),
            updated_at=now,
        )

    except Exception as e:
        print(f"[LeadScoring] Error for {lead.company_name}: {e}")
        return LeadScoreBreakdown(rationale=f"Scoring error: {e}", updated_at=now)
```

- [ ] **Step 2: Write `tradenexus/agent/scoring/breakdown.py`**

Port of `server/agent/scoring/scoreBreakdown.ts` (pure logic):

```python
"""
tradenexus/agent/scoring/breakdown.py

Phase 4 — Score breakdown formatting and utility functions.
Port of server/agent/scoring/scoreBreakdown.ts (pure logic).
"""

from __future__ import annotations

from tradenexus.agent.types import LeadScoreBreakdown


DIMENSION_LABELS: dict[str, str] = {
    "overall": "Overall",
    "location_fit": "Location Fit",
    "product_fit": "Product Fit",
    "buyer_type_fit": "Buyer Type",
    "company_size_fit": "Company Size",
    "evidence_quality": "Evidence Quality",
    "social_activity": "Social Activity",
    "contactability": "Contactability",
    "competitive_opportunity": "Competitive Gap",
    "freshness": "Freshness",
}


def score_bar(value: int, width: int = 10) -> str:
    """Render a value as a unicode bar chart string."""
    filled = round((value / 100) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def score_color(value: int) -> str:
    """Return a hex color for a score value."""
    if value >= 80:
        return "#34d399"
    if value >= 60:
        return "#fbbf24"
    if value >= 40:
        return "#f97316"
    return "#ef4444"


def get_score_label(value: int) -> str:
    """Return a human-readable label for a score value."""
    if value >= 80:
        return "Strong"
    if value >= 60:
        return "Good"
    if value >= 40:
        return "Fair"
    return "Weak"


def format_score_breakdown(score: LeadScoreBreakdown) -> str:
    """Format a LeadScoreBreakdown as a terminal-ready string with bar charts."""
    lines: list[str] = []
    dims = [
        "overall", "location_fit", "product_fit", "buyer_type_fit",
        "company_size_fit", "evidence_quality", "social_activity",
        "contactability", "competitive_opportunity", "freshness",
    ]

    for dim in dims:
        value = getattr(score, dim, 50)
        bar = score_bar(value)
        label = DIMENSION_LABELS.get(dim, dim)
        lines.append(f"{label:<22} {bar} {value}/100")

    if score.rationale:
        lines.append("")
        lines.append(f"Rationale: {score.rationale}")

    return "\n".join(lines)
```

- [ ] **Step 3: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.agent.scoring.lead import score_lead
from tradenexus.agent.scoring.breakdown import format_score_breakdown, score_bar, score_color, get_score_label
print('OK')
"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tradenexus/agent/scoring/
git commit -m "feat: port lead scoring and breakdown modules to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 15: Port planner modules

**Files:**
- Create: `tradenexus/agent/planner/campaign.py`
- Create: `tradenexus/agent/planner/actions.py`

- [ ] **Step 1: Write `tradenexus/agent/planner/campaign.py`**

Port of `server/agent/planner/campaignPlanner.ts` (pure logic):

```python
"""
tradenexus/agent/planner/campaign.py

Phase 5 — Campaign planner: determines which modules to run based on campaign state.
Port of server/agent/planner/campaignPlanner.ts (pure logic).
"""

from __future__ import annotations
import time
from typing import Optional

from tradenexus.models import SearchSession, StrategicContext
from tradenexus.agent.types import AgentPlan, AgentPlanStep


def create_campaign_plan(
    session: SearchSession,
    context: Optional[StrategicContext] = None,
) -> AgentPlan:
    """Create a campaign plan with the right steps based on session state."""
    now = time.time()
    steps: list[AgentPlanStep] = []

    def add_step(state: str, label: str) -> AgentPlanStep:
        return AgentPlanStep(state=state, label=label, status="PENDING")

    # Step 1: Always analyze context first
    steps.append(add_step("ANALYZE_CONTEXT", "Analyze product context and target markets"))

    # Step 2: Discover markets if no region suggestions exist
    if not hasattr(session, "suggestions") or not session.suggestions or len(session.suggestions) == 0:
        steps.append(add_step("DISCOVER_MARKETS", "Discover target markets and regions"))

    # Step 3: Discover leads if none exist or all are DISCOVERED with low count
    leads = getattr(session, "leads", None) or []
    if len(leads) == 0:
        steps.append(add_step("DISCOVER_LEADS", "Search for potential leads"))
        steps.append(add_step("DISCOVER_SOCIAL", "Find leads through social platforms"))
    elif len(leads) < 10:
        steps.append(add_step("DISCOVER_LEADS", "Expand lead pool — currently under 10 leads"))

    # Step 4: Enrich leads that lack evidence or social profiles
    unenriched = sum(1 for l in leads if not getattr(l, "evidence", None))
    no_social = sum(1 for l in leads if not getattr(l, "social_discovery", None))
    if unenriched > 0 or no_social > 0:
        steps.append(add_step("ENRICH_LEADS", f"Enrich {unenriched + no_social} leads with evidence and social data"))

    # Step 5: Verify unverified leads
    unverified = sum(1 for l in leads if not getattr(l, "verification", None))
    if unverified > 0:
        steps.append(add_step("VERIFY_LEADS", f"Verify {unverified} unverified leads"))

    # Step 6: Score unscored leads
    unscored = sum(1 for l in leads if not getattr(l, "score_breakdown", None))
    if unscored > 0:
        steps.append(add_step("SCORE_LEADS", f"Score {unscored} unscored leads"))

    # Step 7: Draft outreach for verified, scored leads with no outreach
    ready = sum(
        1 for l in leads
        if getattr(l, "verification", None)
        and getattr(l, "score_breakdown", None)
        and (not getattr(l, "outreach_drafts", None) or len(l.outreach_drafts) == 0)
    )
    if ready > 0:
        steps.append(add_step("DRAFT_OUTREACH", f"Draft outreach for {ready} qualified leads"))

    # Step 8: Always end with user approval gate
    steps.append(add_step("AWAIT_USER_APPROVAL", "Review and approve next actions"))

    return AgentPlan(
        id=f"plan-{getattr(session, 'id', 'unknown')}-{int(now)}",
        campaign_id=getattr(session, "id", "unknown"),
        steps=steps,
        current_step=0,
        created_at=now,
        updated_at=now,
    )
```

- [ ] **Step 2: Write `tradenexus/agent/planner/actions.py`**

Port of `server/agent/planner/nextBestAction.ts`:

```python
"""
tradenexus/agent/planner/actions.py

Phase 5 — Next best action: recommends next action for a given lead using AI.
Port of server/agent/planner/nextBestAction.ts
"""

from __future__ import annotations
import time

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead
from tradenexus.agent.types import AgentRecommendation
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


VALID_TYPES = {"VERIFY", "ENRICH", "DRAFT_OUTREACH", "PRIORITIZE", "REJECT", "USER_REVIEW", "EXPORT"}
VALID_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}


def recommend_next_actions(lead: Lead) -> list[AgentRecommendation]:
    """Recommend 2-4 next best actions for a lead based on its current state."""
    now = time.time()

    has_verification = bool(lead.verification)
    has_score = bool(lead.score_breakdown)
    has_social = bool(lead.social_discovery)
    has_evidence = bool(lead.evidence)
    has_contact = bool(lead.contact_email or lead.phone_number)

    verification_status = "UNVERIFIED"
    if isinstance(lead.verification, dict):
        verification_status = lead.verification.get("status", "UNVERIFIED")

    overall_score = 0
    if isinstance(lead.score_breakdown, dict):
        overall_score = lead.score_breakdown.get("overall", 0)

    prompt = f"""
You are a Sales Strategy Advisor. Based on the lead's current state, recommend the next best actions.

LEAD:
- Company: {lead.company_name}
- Region: {lead.region}
- Status: {lead.status.value}
- Confidence: {lead.confidence_score}/100
- Has Verification: {has_verification} ({verification_status})
- Has Score: {has_score} (overall: {overall_score}/100)
- Has Social Profiles: {has_social}
- Has Evidence: {has_evidence}
- Has Contact Info: {has_contact}
- Website: {lead.website or 'None'}

Recommend 2-4 next actions. Each action must have:
- type: One of VERIFY, ENRICH, DRAFT_OUTREACH, PRIORITIZE, REJECT, USER_REVIEW, EXPORT
- priority: HIGH, MEDIUM, or LOW
- title: Short action title (max 8 words)
- reason: Why this action is recommended (1 sentence)

Rules:
- If not verified, VERIFY should be HIGH priority
- If scored >= 60 and verified but no outreach, DRAFT_OUTREACH should be HIGH
- If scored < 40, consider REJECT with MEDIUM priority
- Always include at least one actionable item

Return ONLY a JSON array. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
            ),
        )

        if not response.text:
            return _fallback_recommendations(lead, now)

        parsed = extract_json_from_text(response.text)
        if not parsed or not isinstance(parsed, list):
            return _fallback_recommendations(lead, now)

        recs = []
        for i, item in enumerate(parsed[:4]):
            recs.append(
                AgentRecommendation(
                    id=f"rec-{lead.id}-{int(now)}-{i}",
                    type=item.get("type") if item.get("type") in VALID_TYPES else "USER_REVIEW",
                    priority=item.get("priority") if item.get("priority") in VALID_PRIORITIES else "MEDIUM",
                    title=str(item.get("title", "Review this lead")),
                    reason=str(item.get("reason", "No reason provided.")),
                    created_at=now,
                )
            )
        return recs

    except Exception as e:
        print(f"[NextBestAction] Error for {lead.company_name}: {e}")
        return _fallback_recommendations(lead, now)


def _fallback_recommendations(lead: Lead, now: float) -> list[AgentRecommendation]:
    recs: list[AgentRecommendation] = []
    idx = 0

    if not lead.verification:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="VERIFY", priority="HIGH",
                title="Verify lead details",
                reason="Verification has not been completed yet.",
                created_at=now,
            )
        )
        idx += 1

    if not lead.score_breakdown:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="USER_REVIEW", priority="MEDIUM",
                title="Score this lead",
                reason="Lead scoring helps prioritize outreach efforts.",
                created_at=now,
            )
        )
        idx += 1

    if not lead.social_discovery:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="ENRICH", priority="MEDIUM",
                title="Find social profiles",
                reason="Social profiles provide additional contact channels.",
                created_at=now,
            )
        )
        idx += 1

    if not recs:
        recs.append(
            AgentRecommendation(
                id=f"rec-{lead.id}-{int(now)}-{idx}",
                type="USER_REVIEW", priority="LOW",
                title="Review lead status",
                reason="All automated checks complete — manual review recommended.",
                created_at=now,
            )
        )

    return recs
```

- [ ] **Step 3: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.agent.planner.campaign import create_campaign_plan
from tradenexus.agent.planner.actions import recommend_next_actions
print('OK')
"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tradenexus/agent/planner/
git commit -m "feat: port campaign planner and next-best-action modules to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 16: Port memory modules

**Files:**
- Create: `tradenexus/agent/memory/campaign.py`
- Create: `tradenexus/agent/memory/rejection.py`
- Create: `tradenexus/agent/memory/supplier.py`

- [ ] **Step 1: Write `tradenexus/agent/memory/campaign.py`**

Port of `server/agent/memory/campaignMemory.ts` (in-memory store):

```python
"""
tradenexus/agent/memory/campaign.py

Phase 5 — Campaign memory: records and retrieves campaign-level learning events.
Port of server/agent/memory/campaignMemory.ts (pure logic, in-memory store).
"""

from __future__ import annotations
import time

from tradenexus.agent.types import CampaignMemory, MemoryEvent


_memory = CampaignMemory(updated_at=time.time())


def get_campaign_memory() -> CampaignMemory:
    """Return the current in-memory campaign memory."""
    return _memory


def record_memory_event(event: MemoryEvent) -> None:
    """Record a memory event and update derived patterns."""
    _memory.events.append(event)
    _memory.updated_at = time.time()

    # Derive patterns from accumulated events
    if event.type == "LEAD_ACCEPTED" and event.details:
        if event.details not in _memory.preferred_lead_patterns:
            _memory.preferred_lead_patterns.append(event.details)

    if event.type == "LEAD_REJECTED" and event.details:
        if event.details not in _memory.rejected_lead_patterns:
            _memory.rejected_lead_patterns.append(event.details)

    if event.type == "SOCIAL_PROFILE_USEFUL" and event.details:
        platform = event.details
        _memory.platform_usefulness[platform] = _memory.platform_usefulness.get(platform, 0) + 1

    if event.type == "SOCIAL_PROFILE_IRRELEVANT" and event.details:
        platform = event.details
        _memory.platform_usefulness[platform] = _memory.platform_usefulness.get(platform, 0) - 1


def reset_campaign_memory() -> None:
    """Reset campaign memory to initial state."""
    global _memory
    _memory = CampaignMemory(updated_at=time.time())
```

- [ ] **Step 2: Write `tradenexus/agent/memory/rejection.py`**

Port of `server/agent/memory/rejectionPatterns.ts`:

```python
"""
tradenexus/agent/memory/rejection.py

Phase 5 — Rejection patterns: analyzes rejected leads to identify patterns using AI.
Port of server/agent/memory/rejectionPatterns.ts
"""

from __future__ import annotations
import json
import time

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead
from tradenexus.agent.types import CampaignMemory
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def analyze_rejection_patterns(rejected_leads: list[Lead]) -> CampaignMemory:
    """Analyze rejected leads with AI to identify common patterns."""
    if not rejected_leads:
        return CampaignMemory(updated_at=time.time())

    lead_summaries = []
    for l in rejected_leads:
        md = l.match_details
        lead_summaries.append({
            "company": l.company_name,
            "region": l.region,
            "industry": md.industry_fit if md else "Unknown",
            "size": l.employee_count or "Unknown",
            "website": l.website or "None",
            "summary": l.summary or "No summary",
        })

    prompt = f"""
You are a Lead Pattern Analyst. Analyze these REJECTED leads and identify common patterns.

REJECTED LEADS:
{json.dumps(lead_summaries, indent=2)}

Identify:
1. rejectedLeadPatterns: 3-5 strings describing common traits (e.g., "too small", "wrong industry", "no importing history")
2. weakRegions: Array of region names where multiple rejections occurred
3. A brief analysis summary (2-3 sentences)

Return ONLY a JSON object with rejectedLeadPatterns, weakRegions, and analysis fields. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
            ),
        )

        if not response.text:
            return CampaignMemory(updated_at=time.time())

        parsed = extract_json_from_text(response.text)
        if not parsed:
            return CampaignMemory(updated_at=time.time())

        return CampaignMemory(
            rejected_lead_patterns=parsed.get("rejectedLeadPatterns") if isinstance(parsed.get("rejectedLeadPatterns"), list) else [],
            weak_regions=parsed.get("weakRegions") if isinstance(parsed.get("weakRegions"), list) else [],
            updated_at=time.time(),
        )

    except Exception as e:
        print(f"[RejectionPatterns] Analysis failed: {e}")
        return CampaignMemory(updated_at=time.time())
```

- [ ] **Step 3: Write `tradenexus/agent/memory/supplier.py`**

Port of `server/agent/memory/supplierMemory.ts` (pure logic):

```python
"""
tradenexus/agent/memory/supplier.py

Phase 5 — Supplier memory: merges campaign memories across campaigns.
Port of server/agent/memory/supplierMemory.ts (pure logic).
"""

from __future__ import annotations
import time

from tradenexus.agent.types import CampaignMemory


def merge_supplier_memory(existing: CampaignMemory, campaign_memory: CampaignMemory) -> CampaignMemory:
    """Merge two campaign memories, deduplicating events and combining scores."""
    now = time.time()

    # Merge events (newest first), deduplicate by id
    seen_ids = {e.id for e in existing.events}
    new_events = [e for e in campaign_memory.events if e.id not in seen_ids]
    merged_events = (campaign_memory.events + existing.events)[:500]

    # Merge string arrays with dedup, incoming first
    def merge_strings(base: list[str], incoming: list[str]) -> list[str]:
        return list(dict.fromkeys(incoming + base))

    # Merge platform usefulness scores (add values)
    merged_platforms = dict(existing.platform_usefulness)
    for platform, score in campaign_memory.platform_usefulness.items():
        merged_platforms[platform] = merged_platforms.get(platform, 0) + score

    # Merge buyer type performance scores
    merged_buyer_types = dict(existing.buyer_type_performance)
    for buyer_type, score in campaign_memory.buyer_type_performance.items():
        merged_buyer_types[buyer_type] = merged_buyer_types.get(buyer_type, 0) + score

    return CampaignMemory(
        events=merged_events,
        preferred_lead_patterns=merge_strings(existing.preferred_lead_patterns, campaign_memory.preferred_lead_patterns),
        rejected_lead_patterns=merge_strings(existing.rejected_lead_patterns, campaign_memory.rejected_lead_patterns),
        strong_regions=merge_strings(existing.strong_regions, campaign_memory.strong_regions),
        weak_regions=merge_strings(existing.weak_regions, campaign_memory.weak_regions),
        platform_usefulness=merged_platforms,
        buyer_type_performance=merged_buyer_types,
        updated_at=now,
    )
```

- [ ] **Step 4: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.agent.memory.campaign import get_campaign_memory, record_memory_event, reset_campaign_memory
from tradenexus.agent.memory.rejection import analyze_rejection_patterns
from tradenexus.agent.memory.supplier import merge_supplier_memory
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tradenexus/agent/memory/
git commit -m "feat: port campaign memory, rejection patterns, and supplier memory to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 17: Port outreach modules

**Files:**
- Create: `tradenexus/agent/outreach/strategy.py`
- Create: `tradenexus/agent/outreach/drafting.py`
- Create: `tradenexus/agent/outreach/followup.py`

- [ ] **Step 1: Write `tradenexus/agent/outreach/strategy.py`**

Port of `server/agent/outreach/closingStrategy.ts`:

```python
"""
tradenexus/agent/outreach/strategy.py

Phase 6 — Closing strategy: selects the best deal-closing approach for a lead.
Port of server/agent/outreach/closingStrategy.ts
"""

from __future__ import annotations
import time
import json
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import ClosingStrategy
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


VALID_STRATEGY_TYPES = {
    "DIRECT_VALUE_PITCH", "COMPETITIVE_DISPLACEMENT", "EDUCATIONAL_HOOK",
    "PROBLEM_SOLUTION", "PARTNERSHIP_APPROACH", "CASE_STUDY_APPROACH",
}

VALID_PLATFORMS = {
    "cold_email", "linkedin_connection", "linkedin_followup",
    "whatsapp_short", "tradeshow_intro", "distributor_pitch",
}


def generate_closing_strategy(
    lead: Lead,
    product: Optional[ProductDetails] = None,
) -> ClosingStrategy:
    """Select the best closing strategy for a lead based on evidence and profile."""
    now = time.time()
    product_name = product.name if product else "our product"

    evidence_summary = []
    for e in (lead.evidence or [])[:10]:
        if isinstance(e, dict):
            evidence_summary.append({
                "type": e.get("source_type", e.get("sourceType", "?")),
                "title": e.get("title", ""),
                "snippet": (e.get("snippet", "") or "")[:200],
                "confidence": e.get("confidence", 0),
            })

    social_summary = []
    for s in (lead.social_discovery or [])[:10]:
        if isinstance(s, dict):
            social_summary.append({
                "platform": s.get("platform", "?"),
                "activityLevel": s.get("activity_level", s.get("activityLevel", "?")),
                "isOfficial": s.get("is_official_likely", s.get("isOfficialLikely", False)),
                "relevance": (s.get("relevance_notes", s.get("relevanceNotes", "")) or "")[:150],
            })

    has_competitors = bool(lead.competitors)
    competitor_summary = []
    if has_competitors:
        for c in (lead.competitors or []):
            name = c.name if hasattr(c, 'name') else c.get('name', '?')
            weaknesses = (c.weaknesses if hasattr(c, 'weaknesses') else c.get('weaknesses', '')) or ''
            competitor_summary.append(f"{name}: weakness={weaknesses[:100]}")

    overall_score = 0
    if isinstance(lead.score_breakdown, dict):
        overall_score = lead.score_breakdown.get("overall", 0)

    verification_status = "UNVERIFIED"
    if isinstance(lead.verification, dict):
        verification_status = lead.verification.get("status", "UNVERIFIED")

    prompt = f"""
You are a B2B Sales Strategist specializing in international trade. Select the best closing strategy for this lead.

LEAD PROFILE:
- Company: {lead.company_name}
- Region: {lead.region}
- Lead Score: {overall_score}/100
- Verification: {verification_status}
- Has Contact Info: {'Yes' if (lead.contact_email or lead.phone_number) else 'No'}
- Has Social Presence: {'Yes' if social_summary else 'No'}

EVIDENCE GATHERED ({len(evidence_summary)} records):
{json.dumps(evidence_summary, indent=2)}

SOCIAL PROFILES ({len(social_summary)} profiles):
{json.dumps(social_summary, indent=2)}

{'COMPETITORS:\\n' + chr(10).join(competitor_summary) if has_competitors else 'COMPETITORS: None identified'}

PRODUCT: {product_name}

Select ONE closing strategy from:
- DIRECT_VALUE_PITCH: Lead has clear need, strong evidence. Pitch value directly.
- COMPETITIVE_DISPLACEMENT: Competitors identified with known weaknesses.
- EDUCATIONAL_HOOK: Lead may not understand the product category. Educate first.
- PROBLEM_SOLUTION: Lead has specific pain point. Position as the solution.
- PARTNERSHIP_APPROACH: Strategic fit for long-term partnership.
- CASE_STUDY_APPROACH: Similar companies have succeeded. Lead with success story.

Return ONLY a JSON object with: type, rationale, keyTalkingPoints (3-5), evidenceToHighlight (2-4), recommendedPlatform, confidence (0-100).
No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
            ),
        )

        if not response.text:
            return _fallback_strategy(lead, now, "Model returned empty response")

        parsed = extract_json_from_text(response.text)
        if not parsed:
            return _fallback_strategy(lead, now, "Could not parse model response")

        return ClosingStrategy(
            type=parsed.get("type") if parsed.get("type") in VALID_STRATEGY_TYPES else "DIRECT_VALUE_PITCH",
            rationale=str(parsed.get("rationale", "Strategy selected based on lead profile analysis.")),
            key_talking_points=parsed.get("keyTalkingPoints") if isinstance(parsed.get("keyTalkingPoints"), list) else [],
            evidence_to_highlight=parsed.get("evidenceToHighlight") if isinstance(parsed.get("evidenceToHighlight"), list) else [],
            recommended_platform=parsed.get("recommendedPlatform") if parsed.get("recommendedPlatform") in VALID_PLATFORMS else "cold_email",
            confidence=max(0, min(100, round(float(parsed.get("confidence", 70))))),
            generated_at=now,
        )

    except Exception as e:
        print(f"[ClosingStrategy] Error for {lead.company_name}: {e}")
        return _fallback_strategy(lead, now, f"Strategy error: {e}")


def _fallback_strategy(lead: Lead, now: float, reason: str) -> ClosingStrategy:
    has_competitors = bool(lead.competitors)
    has_social = bool(lead.social_discovery)
    return ClosingStrategy(
        type="COMPETITIVE_DISPLACEMENT" if has_competitors else "DIRECT_VALUE_PITCH",
        rationale=f"Fallback strategy: {reason}.",
        key_talking_points=[
            "Our product quality and competitive pricing",
            "Reliable supply chain and on-time delivery",
            "Flexible order quantities and customization options",
        ],
        recommended_platform="linkedin_connection" if has_social else "cold_email",
        confidence=30,
        generated_at=now,
    )
```

- [ ] **Step 2: Write `tradenexus/agent/outreach/drafting.py`**

Port of `server/agent/outreach/messageDrafting.ts`:

```python
"""
tradenexus/agent/outreach/drafting.py

Phase 6 — Message drafting: generates strategy-guided, evidence-citing outreach drafts.
Port of server/agent/outreach/messageDrafting.ts
"""

from __future__ import annotations
import time
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead, StrategicContext
from tradenexus.agent.types import OutreachDraft, ClosingStrategy
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


PLATFORM_GUIDANCE = {
    "cold_email": {"maxLength": 250, "tone": "professional and concise", "needsSubject": True},
    "linkedin_connection": {"maxLength": 200, "tone": "personal and brief — this is a connection request note", "needsSubject": False},
    "linkedin_followup": {"maxLength": 350, "tone": "warm follow-up referencing prior contact", "needsSubject": False},
    "whatsapp_short": {"maxLength": 150, "tone": "casual, direct, mobile-friendly", "needsSubject": False},
    "tradeshow_intro": {"maxLength": 200, "tone": "in-person follow-up energy, reference the event", "needsSubject": True},
    "distributor_pitch": {"maxLength": 300, "tone": "business-focused, emphasize margins and logistics", "needsSubject": True},
}


def generate_outreach_draft(
    lead: Lead,
    draft_type: str,
    strategy: ClosingStrategy,
    context: Optional[StrategicContext] = None,
) -> OutreachDraft:
    """Generate an outreach draft guided by a closing strategy."""
    now = time.time()
    guidance = PLATFORM_GUIDANCE.get(draft_type, PLATFORM_GUIDANCE["cold_email"])
    product_name = context.product_identity if context else "our product"

    # Collect relevant evidence snippets
    evidence_available = lead.evidence or []
    relevant_evidence = []
    for e in evidence_available[:10]:
        title = e.get("title", "") if isinstance(e, dict) else getattr(e, "title", "")
        snippet = e.get("snippet", "") if isinstance(e, dict) else getattr(e, "snippet", "")
        for highlight in strategy.evidence_to_highlight:
            if highlight.lower() in (title or "").lower() or highlight.lower() in (snippet or "").lower():
                relevant_evidence.append(e)
                break

    evidence_ids = []
    for e in relevant_evidence[:3]:
        eid = e.get("id", "") if isinstance(e, dict) else getattr(e, "id", "")
        if eid:
            evidence_ids.append(eid)

    evidence_snippets = []
    for e in relevant_evidence[:3]:
        st = e.get("source_type", e.get("sourceType", "?")) if isinstance(e, dict) else getattr(e, "source_type", "?")
        title = e.get("title", "") if isinstance(e, dict) else getattr(e, "title", "")
        snippet = (e.get("snippet", "") if isinstance(e, dict) else getattr(e, "snippet", "")) or ""
        evidence_snippets.append(f"[{st}] {title}: {snippet[:150]}")

    # Social contact hints
    social_contact_info = []
    for s in (lead.social_discovery or [])[:5]:
        hints = s.get("contact_hints", s.get("contactHints", [])) if isinstance(s, dict) else getattr(s, "contact_hints", [])
        if hints:
            social_contact_info.extend(hints)
    social_contact_info = social_contact_info[:3]

    prompt = f"""
You are a B2B Sales Copywriter. Write an outreach message for the following lead.

CLOSING STRATEGY: {strategy.type}
Strategy Rationale: {strategy.rationale}

KEY TALKING POINTS TO INCLUDE:
{chr(10).join(f"{i+1}. {p}" for i, p in enumerate(strategy.key_talking_points))}

SUPPORTING EVIDENCE:
{chr(10).join(evidence_snippets) if evidence_snippets else 'No specific evidence available — use general value propositions.'}

LEAD:
- Company: {lead.company_name}
- Region: {lead.region}
- Contact: {lead.contact_email or lead.phone_number or 'No direct contact — use company channels'}
- Website: {lead.website or 'None'}
{"- Social Contact Hints: " + ", ".join(social_contact_info) if social_contact_info else ""}

PRODUCT: {product_name}

PLATFORM: {draft_type}
{"Include a subject line." if guidance['needsSubject'] else 'No subject line needed.'}
Max length: ~{guidance['maxLength']} characters.
Tone: {guidance['tone']}

IMPORTANT:
- Weave in the strategy's talking points naturally — don't list them
- Reference specific evidence when it adds credibility
- End with a clear, low-friction call to action
- Do NOT use placeholders like [Company Name] — use the actual company name: {lead.company_name}

Return ONLY a JSON object with 'subject' and 'body' fields. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
            ),
        )

        if not response.text:
            return _fallback_draft(lead, draft_type, strategy, now, evidence_ids, "Model returned empty response")

        parsed = extract_json_from_text(response.text)
        if not parsed or not parsed.get("body"):
            return _fallback_draft(lead, draft_type, strategy, now, evidence_ids, "Could not parse model response")

        return OutreachDraft(
            id=f"draft-{lead.id}-{int(now)}",
            type=draft_type,
            subject=parsed.get("subject") if guidance["needsSubject"] else None,
            body=str(parsed["body"]),
            evidence_ids=evidence_ids,
            created_at=now,
        )

    except Exception as e:
        print(f"[MessageDrafting] Error for {lead.company_name}: {e}")
        return _fallback_draft(lead, draft_type, strategy, now, evidence_ids, f"Drafting error: {e}")


def _fallback_draft(
    lead: Lead,
    draft_type: str,
    strategy: ClosingStrategy,
    now: float,
    evidence_ids: list[str],
    reason: str,
) -> OutreachDraft:
    talking_points = " ".join(strategy.key_talking_points[:2]) if strategy.key_talking_points else "we see a strong fit"

    bodies = {
        "cold_email": f"Subject: Partnership Opportunity for {lead.company_name}\n\nDear {lead.company_name} team,\n\nI'm reaching out because {talking_points}.\n\nWe specialize in high-quality manufacturing with reliable delivery. I'd love to schedule a brief call to explore how we can support your supply chain.\n\nBest regards",
        "linkedin_connection": f"Hi, I've been following {lead.company_name}'s work in {lead.region}. {talking_points}. Would love to connect and explore potential collaboration.",
        "linkedin_followup": f"Hi again, following up on my previous message. {talking_points}. Happy to share more details about how we've helped similar companies — just let me know if you'd like to chat.",
        "whatsapp_short": f"Hi! This is regarding a potential supply partnership with {lead.company_name}. {talking_points}. Would you be open to a quick chat?",
        "tradeshow_intro": f"Subject: Great to connect at the show\n\nHi {lead.company_name} team,\n\nIt was great meeting you. {talking_points}.\n\nLet me know if you'd like to continue the discussion.\n\nBest regards",
        "distributor_pitch": f"Subject: Distribution Partnership — {lead.company_name}\n\nDear {lead.company_name} team,\n\nWe're looking for a distribution partner in {lead.region} and {lead.company_name} stands out. {talking_points}.\n\nOur products offer competitive margins and reliable supply. I'd love to discuss a potential partnership.\n\nBest regards",
    }

    return OutreachDraft(
        id=f"draft-{lead.id}-{int(now)}",
        type=draft_type,
        subject=f"Partnership Opportunity for {lead.company_name}" if draft_type in ("cold_email", "tradeshow_intro", "distributor_pitch") else None,
        body=bodies.get(draft_type, bodies["cold_email"]),
        evidence_ids=evidence_ids,
        created_at=now,
    )
```

- [ ] **Step 3: Write `tradenexus/agent/outreach/followup.py`**

Port of `server/agent/outreach/followUpPlanning.ts`:

```python
"""
tradenexus/agent/outreach/followup.py

Phase 6 — Follow-up planning: builds multi-step closing sequences.
Port of server/agent/outreach/followUpPlanning.ts
"""

from __future__ import annotations
import time
from typing import Optional

from google import genai
from google.genai import types as gtypes

from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.models import Lead
from tradenexus.agent.types import ClosingStrategy, OutreachSequence, OutreachSequenceStep
from tradenexus.utils import extract_json_from_text


def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def _thinking(model: str) -> dict:
    return build_thinking_config(model)


def plan_follow_up_sequence(
    lead: Lead,
    initial_draft_id: str,
    strategy: ClosingStrategy,
) -> OutreachSequence:
    """Plan a multi-step follow-up sequence to close a deal."""
    now = time.time()

    has_email = bool(lead.contact_email)
    has_phone = bool(lead.phone_number)
    has_social = bool(lead.social_discovery)
    has_linkedin = False
    if lead.social_discovery:
        for s in lead.social_discovery:
            p = s.get("platform", "") if isinstance(s, dict) else getattr(s, "platform", "")
            if p == "linkedin":
                has_linkedin = True
                break

    prompt = f"""
You are a B2B Sales Cadence Planner. Design a multi-step follow-up sequence to close this deal.

LEAD: {lead.company_name}
REGION: {lead.region}
CLOSING STRATEGY: {strategy.type}
INITIAL DRAFT ALREADY SENT via: {strategy.recommended_platform}
CHANNELS AVAILABLE:
- Email: {'Yes' if has_email else 'No'}
- Phone/SMS: {'Yes' if has_phone else 'No'}
- LinkedIn: {'Yes' if has_linkedin else 'No'}
- Social: {'Yes' if has_social else 'No'}

STRATEGY TALKING POINTS:
{chr(10).join(f"{i+1}. {p}" for i, p in enumerate(strategy.key_talking_points))}

Plan 3-5 follow-up steps. For each: step (1-based), type, timing, goal.

Rules:
- Vary the channel — don't send 3 emails in a row
- Escalate value over time
- Space steps 3-7 days between touches
- Last step should be a soft breakpoint

Return ONLY a JSON object with steps array, totalDays, and rationale. No markdown wrapping.
"""

    try:
        client = _client()
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                **_thinking(DEFAULT_MODEL),
            ),
        )

        if not response.text:
            return _fallback_sequence(lead, strategy, now, "Model returned empty response")

        parsed = extract_json_from_text(response.text)
        if not parsed or not isinstance(parsed.get("steps"), list):
            return _fallback_sequence(lead, strategy, now, "Could not parse model response")

        steps = []
        for s in parsed["steps"][:5]:
            steps.append(
                OutreachSequenceStep(
                    step=int(s.get("step", len(steps) + 1)),
                    type=str(s.get("type", "cold_email")),
                    timing=str(s.get("timing", "")),
                    goal=str(s.get("goal", "Continue engagement")),
                )
            )

        return OutreachSequence(
            id=f"seq-{lead.id}-{int(now)}",
            lead_id=lead.id,
            strategy_type=strategy.type,
            steps=steps,
            total_days=int(parsed.get("totalDays", 14)),
            rationale=str(parsed.get("rationale", "Multi-step follow-up sequence.")),
            generated_at=now,
        )

    except Exception as e:
        print(f"[FollowUpPlanning] Error for {lead.company_name}: {e}")
        return _fallback_sequence(lead, strategy, now, f"Sequence error: {e}")


def _fallback_sequence(lead: Lead, strategy: ClosingStrategy, now: float, reason: str) -> OutreachSequence:
    has_linkedin = False
    if lead.social_discovery:
        for s in lead.social_discovery:
            p = s.get("platform", "") if isinstance(s, dict) else getattr(s, "platform", "")
            if p == "linkedin":
                has_linkedin = True
                break

    return OutreachSequence(
        id=f"seq-{lead.id}-{int(now)}",
        lead_id=lead.id,
        strategy_type=strategy.type,
        steps=[
            OutreachSequenceStep(step=1, type="linkedin_followup" if has_linkedin else "cold_email", timing="3-4 days after initial", goal="Reinforce key value proposition on a second channel"),
            OutreachSequenceStep(step=2, type="cold_email", timing="1 week after Step 1", goal="Share additional detail — case study, spec sheet, or pricing advantage"),
            OutreachSequenceStep(step=3, type="whatsapp_short", timing="5-7 days after Step 2", goal="Brief, personal check-in. If no response, pause and reassess."),
        ],
        total_days=16,
        rationale=f"Fallback 3-step sequence: {reason}",
        generated_at=now,
    )
```

- [ ] **Step 4: Verify imports**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
from tradenexus.agent.outreach.strategy import generate_closing_strategy
from tradenexus.agent.outreach.drafting import generate_outreach_draft
from tradenexus.agent.outreach.followup import plan_follow_up_sequence
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tradenexus/agent/outreach/
git commit -m "feat: port closing strategy, message drafting, and follow-up planning to Python

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 18: Final verification — ensure everything imports and CLI works

- [ ] **Step 1: Full import chain test**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python -c "
# Core
from tradenexus.core.context import extract_search_strategy_from_assets
from tradenexus.core.markets import analyze_markets, generate_market_report
from tradenexus.core.leads import search_for_leads, verify_lead
from tradenexus.core.prospecting import generate_prospecting_message

# Agent — discovery
from tradenexus.agent.discovery.social import discover_social_for_company, discover_leads_from_social
from tradenexus.agent.discovery.social_to_lead import social_profiles_to_leads
from tradenexus.agent.discovery.maps import extract_maps_evidence
from tradenexus.agent.discovery.web import discover_leads_from_web
from tradenexus.agent.discovery.directory import discover_from_directories

# Agent — enrichment
from tradenexus.agent.enrichment.contact import enrich_contact_info
from tradenexus.agent.enrichment.social import enrich_social_profiles
from tradenexus.agent.enrichment.website import enrich_from_website

# Agent — verification
from tradenexus.agent.verification.lead import verify_lead as agent_verify_lead
from tradenexus.agent.verification.evidence import find_evidence_conflicts
from tradenexus.agent.verification.social import verify_social_profile

# Agent — scoring
from tradenexus.agent.scoring.lead import score_lead
from tradenexus.agent.scoring.breakdown import format_score_breakdown

# Agent — planner
from tradenexus.agent.planner.campaign import create_campaign_plan
from tradenexus.agent.planner.actions import recommend_next_actions

# Agent — memory
from tradenexus.agent.memory.campaign import get_campaign_memory, record_memory_event
from tradenexus.agent.memory.rejection import analyze_rejection_patterns
from tradenexus.agent.memory.supplier import merge_supplier_memory

# Agent — outreach
from tradenexus.agent.outreach.strategy import generate_closing_strategy
from tradenexus.agent.outreach.drafting import generate_outreach_draft
from tradenexus.agent.outreach.followup import plan_follow_up_sequence

# Agent types
from tradenexus.agent.types import (
    DiscoveryEvidence, SocialProfileEvidence, LeadVerification, VerificationCheck,
    LeadScoreBreakdown, AgentPlan, AgentPlanStep, AgentRecommendation,
    OutreachDraft, ClosingStrategy, OutreachSequence, CampaignMemory, MemoryEvent,
)

print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 2: CLI info command still works**

```bash
cd /home/samu2505/SAAS/tradenexus-cli && python main.py info
```

Expected: Shows API key and config (same as before migration).

- [ ] **Step 3: Verify file count**

```bash
find tradenexus -name "*.py" | wc -l
```

Expected: 35+ Python files.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: final verification — all modules import correctly

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```
