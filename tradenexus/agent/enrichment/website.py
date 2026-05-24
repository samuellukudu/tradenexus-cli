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
