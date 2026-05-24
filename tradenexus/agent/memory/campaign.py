"""
tradenexus/agent/memory/campaign.py

Phase 5 -- Campaign memory: records and retrieves campaign-level learning events.
Port of server/agent/memory/campaignMemory.ts (pure logic, in-memory store).
"""

from __future__ import annotations
import time

from tradenexus.agent.types import CampaignMemory, MemoryEvent


_memory = CampaignMemory(updated_at=time.time())


def get_campaign_memory() -> CampaignMemory:
    """Return the current in-memory campaign memory."""
    return _memory


def record_memory_event(event: MemoryEvent) -> None:
    """Record a memory event and update derived patterns."""
    _memory.events.append(event)
    _memory.updated_at = time.time()

    # Derive patterns from accumulated events
    if event.type == "LEAD_ACCEPTED" and event.details:
        if event.details not in _memory.preferred_lead_patterns:
            _memory.preferred_lead_patterns.append(event.details)

    if event.type == "LEAD_REJECTED" and event.details:
        if event.details not in _memory.rejected_lead_patterns:
            _memory.rejected_lead_patterns.append(event.details)

    if event.type == "SOCIAL_PROFILE_USEFUL" and event.details:
        platform = event.details
        _memory.platform_usefulness[platform] = _memory.platform_usefulness.get(platform, 0) + 1

    if event.type == "SOCIAL_PROFILE_IRRELEVANT" and event.details:
        platform = event.details
        _memory.platform_usefulness[platform] = _memory.platform_usefulness.get(platform, 0) - 1


def reset_campaign_memory() -> None:
    """Reset campaign memory to initial state."""
    global _memory
    _memory = CampaignMemory(updated_at=time.time())
