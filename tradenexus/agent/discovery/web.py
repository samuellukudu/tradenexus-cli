"""
tradenexus/agent/discovery/web.py

Phase 1 — Wraps existing search_for_leads and attaches DiscoveryEvidence to each lead.
Port of server/agent/discovery/webDiscovery.ts
"""

from __future__ import annotations
import uuid
import time

from tradenexus.models import Lead, ProductDetails
from tradenexus.agent.types import DiscoveryEvidence
from tradenexus.core.leads import search_for_leads


def discover_leads_from_web(product: ProductDetails) -> list[Lead]:
    """Search for leads and attach structured evidence records to each."""
    leads = search_for_leads(product)
    now = time.time()

    enriched: list[Lead] = []
    for lead in leads:
        evidence_records: list[DiscoveryEvidence] = []

        # Wrap source URL as web evidence
        if lead.source_url:
            evidence_records.append(
                DiscoveryEvidence(
                    id=str(uuid.uuid4()),
                    source_type="web",
                    url=lead.source_url,
                    title=lead.company_name,
                    snippet=lead.summary,
                    confidence=lead.confidence_score / 100,
                    found_at=now,
                    found_by="webDiscovery",
                    validation_status="UNVERIFIED",
                    extracted_fields={
                        "companyName": lead.company_name,
                        "website": lead.website or "",
                        "region": lead.region,
                        "address": lead.address or "",
                    },
                )
            )

        # Wrap Google Maps URL as maps evidence
        if lead.google_maps_url:
            evidence_records.append(
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
                        "address": lead.address or "",
                        "companyName": lead.company_name,
                    },
                )
            )

        # Wrap sources array items as additional web evidence
        if lead.sources:
            for source_url in lead.sources:
                if source_url and source_url != lead.source_url:
                    evidence_records.append(
                        DiscoveryEvidence(
                            id=str(uuid.uuid4()),
                            source_type="web",
                            url=source_url,
                            confidence=0.7,
                            found_at=now,
                            found_by="webDiscovery",
                            validation_status="UNVERIFIED",
                        )
                    )

        lead.evidence = evidence_records
        lead.last_agent_action = "webDiscovery"
        enriched.append(lead)

    return enriched
