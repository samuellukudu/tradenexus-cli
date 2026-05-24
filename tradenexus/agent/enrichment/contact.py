"""
tradenexus/agent/enrichment/contact.py

Phase 4 — Contact enrichment: finds email/phone/contact details for leads.
Port of server/agent/enrichment/contactEnrichment.ts (stub).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from tradenexus.models import Lead


@dataclass
class ContactInfo:
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    source: str = ""
    confidence: float = 0.0


def enrich_contact_info(lead: Lead) -> list[ContactInfo]:
    """Find email/phone/contact details for a lead. Not yet implemented."""
    raise NotImplementedError("Contact enrichment not yet implemented (Phase 4)")
