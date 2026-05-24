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
