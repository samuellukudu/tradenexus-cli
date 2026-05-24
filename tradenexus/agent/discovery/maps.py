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
