"""
tradenexus/core/markets.py

Market analysis and intelligence reports.
Port of analyzeMarkets() and generateMarketReport() from geminiService.ts.
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


def analyze_markets(
    product_name: str,
    product_description: str,
    continent: Optional[str] = None,
    countries: Optional[list[str]] = None,
    product_assets: Optional[list[ProductAsset]] = None,
    pre_computed_context: Optional[StrategicContext] = None,
    supplier_country: str = "China",
) -> list[RegionSuggestion]:
    """Find the top 9 export markets for a product.

    Port of analyzeMarkets() from geminiService.ts.
    """
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


def generate_market_report(product: ProductDetails, region: str) -> MarketReport:
    """Generate a full market intelligence report with Google Search grounding.

    Port of generateMarketReport() from geminiService.ts.
    """
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
