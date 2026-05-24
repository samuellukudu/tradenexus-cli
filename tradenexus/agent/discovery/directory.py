"""
tradenexus/agent/discovery/directory.py

Phase 3+ — Directory discovery: searches business directories and company registries.
Port of server/agent/discovery/directoryDiscovery.ts (stub).
"""

from __future__ import annotations

from tradenexus.models import ProductDetails
from tradenexus.agent.types import DiscoveryEvidence


def discover_from_directories(product: ProductDetails) -> list[DiscoveryEvidence]:
    """Search business directories for leads. Not yet implemented."""
    raise NotImplementedError("Directory discovery not yet implemented (Phase 3+)")
