"""
tradenexus/agent/memory/rejection.py

Phase 5 -- Rejection patterns: analyzes rejected leads to identify patterns using AI.
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
