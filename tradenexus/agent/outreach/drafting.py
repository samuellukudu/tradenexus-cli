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
