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
