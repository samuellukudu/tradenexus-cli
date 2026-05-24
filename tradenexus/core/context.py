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
