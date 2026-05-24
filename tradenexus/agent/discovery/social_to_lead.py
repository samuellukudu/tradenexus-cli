"""
tradenexus/agent/discovery/social_to_lead.py

Phase 3 — Convert SocialProfileEvidence[] to Lead[] objects.
Port of server/agent/discovery/socialToLead.ts (pure logic, no AI).
"""

from __future__ import annotations
import uuid
import time

from tradenexus.models import Lead, LeadStatus, InteractionLog, SocialProfile
from tradenexus.agent.types import SocialProfileEvidence


SOCIAL_VECTOR_PREFIX = "Social:"


def social_profiles_to_leads(
    profiles: list[SocialProfileEvidence],
    region: str,
) -> list[Lead]:
    """Group social profiles by company name and convert to Lead objects."""
    now = time.time()

    # Group profiles by company name to avoid duplicates
    by_company: dict[str, list[SocialProfileEvidence]] = {}
    for profile in profiles:
        name = (
            profile.extracted_fields.get("companyName")
            or profile.title
            or "Unknown Company"
        )
        key = name.lower().strip()
        if key not in by_company:
            by_company[key] = []
        by_company[key].append(profile)

    leads: list[Lead] = []
    for company_profiles in by_company.values():
        primary = company_profiles[0]
        company_name = (
            primary.extracted_fields.get("companyName")
            or primary.title
            or "Unknown Company"
        )
        website = primary.extracted_fields.get("website") or None

        # Collect unique platforms for the search vector
        platforms = list({p.platform for p in company_profiles})
        vector_name = f"{SOCIAL_VECTOR_PREFIX} {'/'.join(platforms)}"

        # Extract contact hints from all profiles
        all_contact_hints: list[str] = []
        for p in company_profiles:
            all_contact_hints.extend(p.contact_hints or [])
        contact_info = ", ".join(list(dict.fromkeys(all_contact_hints))) or None

        # Best confidence across all profiles
        best_confidence = max(p.confidence for p in company_profiles)

        # Best activity level across profiles
        activity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}
        best_activity = max(
            company_profiles,
            key=lambda p: activity_order.get(p.activity_level, 0),
        ).activity_level

        lead = Lead(
            id=str(uuid.uuid4()),
            company_name=str(company_name),
            website=str(website) if website else None,
            region=region,
            status=LeadStatus.DISCOVERED,
            confidence_score=round(best_confidence * 100),
            summary=primary.relevance_notes or primary.snippet,
            social_profiles=[
                SocialProfile(platform=p.platform, url=p.url)
                for p in company_profiles
            ],
            social_discovery=[p for p in company_profiles],
            search_vector=vector_name,
            employee_count=primary.extracted_fields.get("employeeCount") or None,
            last_agent_action="socialDiscovery",
            logs=[
                InteractionLog(
                    timestamp=time.strftime("%H:%M:%S", time.localtime(now)),
                    actor="SYSTEM",
                    message=(
                        f"Lead discovered via social media on {', '.join(platforms)}.\n"
                        f"Activity Level: {best_activity}\n"
                        f"Platforms found: {len(company_profiles)} profile(s)"
                    ),
                )
            ],
        )
        leads.append(lead)

    return leads
