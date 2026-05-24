# Agent Pipeline Migration — Python Port

## Goal

Port the entire Express agent pipeline (18 modules, 6 phases) from `tradenexus-ai-sales-agent/server/agent/` to the Python CLI at `tradenexus-cli/tradenexus/agent/`. Also refactor the monolithic `tradenexus/gemini_service.py` (619 lines) into focused `tradenexus/core/` modules.

## Non-goals

- No API endpoints — pure Python modules only
- No changes to the existing CLI commands in `main.py` (imports updated, behavior unchanged)
- No Firebase or external persistence for agent state (in-memory for now)

## Package Structure (target)

```
tradenexus-cli/
├── main.py
├── tradenexus/
│   ├── __init__.py
│   ├── config.py                    # (unchanged)
│   ├── utils.py                     # (unchanged, maybe added extract_json)
│   ├── models.py                    # Extended with agent pipeline types
│   ├── output.py                    # (unchanged)
│   ├── session.py                   # (unchanged)
│   │
│   ├── core/                        # REFACTORED from gemini_service.py
│   │   ├── __init__.py
│   │   ├── context.py               # extract_search_strategy_from_assets
│   │   ├── markets.py               # analyze_markets, generate_market_report
│   │   ├── leads.py                 # search_for_leads, verify_lead
│   │   └── prospecting.py           # generate_prospecting_message
│   │
│   └── agent/                       # NEW
│       ├── __init__.py
│       ├── types.py                 # Agent dataclasses (VerificationCheck, etc.)
│       │
│       ├── discovery/
│       │   ├── __init__.py
│       │   ├── social.py            # discover_social_for_company, discover_leads_from_social
│       │   ├── social_to_lead.py    # social_profiles_to_leads() — pure logic
│       │   ├── maps.py              # extract_maps_evidence() — pure logic
│       │   ├── directory.py         # extract_directory_evidence() — pure logic
│       │   └── web.py               # extract_web_evidence() — pure logic
│       │
│       ├── enrichment/
│       │   ├── __init__.py
│       │   ├── contact.py           # enrich_contact_info() — pure logic
│       │   ├── social.py            # enrich_social_profiles() — pure logic
│       │   └── website.py           # enrich_website_data() — pure logic
│       │
│       ├── verification/
│       │   ├── __init__.py
│       │   ├── lead.py              # verify_lead() — AI call
│       │   ├── evidence.py          # find_evidence_conflicts() — pure logic
│       │   └── social.py            # verify_social_profile() — stub
│       │
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── lead.py              # score_lead() — AI call
│       │   └── breakdown.py         # format_score_breakdown() — pure logic
│       │
│       ├── planner/
│       │   ├── __init__.py
│       │   ├── campaign.py          # create_campaign_plan() — pure logic
│       │   └── actions.py           # recommend_next_actions() — AI call
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── campaign.py          # CampaignMemory store — pure logic
│       │   ├── rejection.py         # analyze_rejection_patterns() — AI call
│       │   └── supplier.py          # SupplierMemory store — pure logic
│       │
│       └── outreach/
│           ├── __init__.py
│           ├── strategy.py          # generate_closing_strategy() — AI call
│           ├── drafting.py          # generate_outreach_draft() — AI call
│           └── followup.py          # plan_follow_up_sequence() — AI call
```

## Conventions

### Absolute imports only
```python
from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config
from tradenexus.utils import extract_json_from_text, extract_grounding_sources
from tradenexus.models import Lead, StrategicContext
from tradenexus.agent.types import VerificationCheck, LeadScoreBreakdown
```

### No base class — shared utility imports
Every AI-calling module gets its client the same way:
```python
from google import genai
from google.genai import types as gtypes
from tradenexus.config import get_api_key, DEFAULT_MODEL, build_thinking_config

def _client() -> genai.Client:
    return genai.Client(api_key=get_api_key())
```

Pure-logic modules have zero AI imports — only `tradenexus.models` and `tradenexus.agent.types`.

### Function naming
All public agent functions are verbs: `discover_social_for_company()`, `score_lead()`, `generate_closing_strategy()`. This matches the Python ecosystem convention even though the TS originals use camelCase.

## Implementation order

1. **Split `gemini_service.py` → `core/`** (no behavioral change, just reorganization)
2. **Update `main.py`** imports to use `tradenexus.core.*`
3. **Add `agent/types.py`** with all agent-specific dataclasses
4. **Port agent modules** in dependency order:
   - Pure-logic modules first (memory, enrichment, social_to_lead, evidence, breakdown)
   - AI-call modules second (discovery/social, verification/lead, scoring/lead, planner/actions, memory/rejection, outreach/*)
5. **Delete `gemini_service.py`** once `core/` and all imports are verified

## Files to delete

- `tradenexus/gemini_service.py` — replaced by `core/`

## Files to create (22 files)

- `tradenexus/core/__init__.py`
- `tradenexus/core/context.py`
- `tradenexus/core/markets.py`
- `tradenexus/core/leads.py`
- `tradenexus/core/prospecting.py`
- `tradenexus/agent/__init__.py`
- `tradenexus/agent/types.py`
- `tradenexus/agent/discovery/__init__.py`
- `tradenexus/agent/discovery/social.py`
- `tradenexus/agent/discovery/social_to_lead.py`
- `tradenexus/agent/discovery/maps.py`
- `tradenexus/agent/discovery/directory.py`
- `tradenexus/agent/discovery/web.py`
- `tradenexus/agent/enrichment/__init__.py`
- `tradenexus/agent/enrichment/contact.py`
- `tradenexus/agent/enrichment/social.py`
- `tradenexus/agent/enrichment/website.py`
- `tradenexus/agent/verification/__init__.py`
- `tradenexus/agent/verification/lead.py`
- `tradenexus/agent/verification/evidence.py`
- `tradenexus/agent/verification/social.py`
- `tradenexus/agent/scoring/__init__.py`
- `tradenexus/agent/scoring/lead.py`
- `tradenexus/agent/scoring/breakdown.py`
- `tradenexus/agent/planner/__init__.py`
- `tradenexus/agent/planner/campaign.py`
- `tradenexus/agent/planner/actions.py`
- `tradenexus/agent/memory/__init__.py`
- `tradenexus/agent/memory/campaign.py`
- `tradenexus/agent/memory/rejection.py`
- `tradenexus/agent/memory/supplier.py`
- `tradenexus/agent/outreach/__init__.py`
- `tradenexus/agent/outreach/strategy.py`
- `tradenexus/agent/outreach/drafting.py`
- `tradenexus/agent/outreach/followup.py`

## Verification

After migration, `python main.py info` and `python main.py analyze-markets` must work identically to before.
