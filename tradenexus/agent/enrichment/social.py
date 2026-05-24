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
