"""
tradenexus/agent/memory/supplier.py

Phase 5 -- Supplier memory: merges campaign memories across campaigns.
Port of server/agent/memory/supplierMemory.ts (pure logic).
"""

from __future__ import annotations
import time

from tradenexus.agent.types import CampaignMemory


def merge_supplier_memory(existing: CampaignMemory, campaign_memory: CampaignMemory) -> CampaignMemory:
    """Merge two campaign memories, deduplicating events and combining scores."""
    now = time.time()

    # Merge events (newest first), deduplicate by id
    seen_ids = {e.id for e in existing.events}
    new_events = [e for e in campaign_memory.events if e.id not in seen_ids]
    merged_events = (campaign_memory.events + existing.events)[:500]

    # Merge string arrays with dedup, incoming first
    def merge_strings(base: list[str], incoming: list[str]) -> list[str]:
        return list(dict.fromkeys(incoming + base))

    # Merge platform usefulness scores (add values)
    merged_platforms = dict(existing.platform_usefulness)
    for platform, score in campaign_memory.platform_usefulness.items():
        merged_platforms[platform] = merged_platforms.get(platform, 0) + score

    # Merge buyer type performance scores
    merged_buyer_types = dict(existing.buyer_type_performance)
    for buyer_type, score in campaign_memory.buyer_type_performance.items():
        merged_buyer_types[buyer_type] = merged_buyer_types.get(buyer_type, 0) + score

    return CampaignMemory(
        events=merged_events,
        preferred_lead_patterns=merge_strings(existing.preferred_lead_patterns, campaign_memory.preferred_lead_patterns),
        rejected_lead_patterns=merge_strings(existing.rejected_lead_patterns, campaign_memory.rejected_lead_patterns),
        strong_regions=merge_strings(existing.strong_regions, campaign_memory.strong_regions),
        weak_regions=merge_strings(existing.weak_regions, campaign_memory.weak_regions),
        platform_usefulness=merged_platforms,
        buyer_type_performance=merged_buyer_types,
        updated_at=now,
    )
