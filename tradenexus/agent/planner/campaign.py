"""
tradenexus/agent/planner/campaign.py

Phase 5 — Campaign planner: determines which modules to run based on campaign state.
Port of server/agent/planner/campaignPlanner.ts (pure logic).
"""

from __future__ import annotations
import time
from typing import Optional

from tradenexus.models import SearchSession, StrategicContext
from tradenexus.agent.types import AgentPlan, AgentPlanStep


def create_campaign_plan(
    session: SearchSession,
    context: Optional[StrategicContext] = None,
) -> AgentPlan:
    """Create a campaign plan with the right steps based on session state."""
    now = time.time()
    steps: list[AgentPlanStep] = []

    def add_step(state: str, label: str) -> AgentPlanStep:
        return AgentPlanStep(state=state, label=label, status="PENDING")

    # Step 1: Always analyze context first
    steps.append(add_step("ANALYZE_CONTEXT", "Analyze product context and target markets"))

    # Step 2: Discover markets if no region suggestions exist
    if not hasattr(session, "suggestions") or not session.suggestions or len(session.suggestions) == 0:
        steps.append(add_step("DISCOVER_MARKETS", "Discover target markets and regions"))

    # Step 3: Discover leads if none exist or all are DISCOVERED with low count
    leads = getattr(session, "leads", None) or []
    if len(leads) == 0:
        steps.append(add_step("DISCOVER_LEADS", "Search for potential leads"))
        steps.append(add_step("DISCOVER_SOCIAL", "Find leads through social platforms"))
    elif len(leads) < 10:
        steps.append(add_step("DISCOVER_LEADS", "Expand lead pool — currently under 10 leads"))

    # Step 4: Enrich leads that lack evidence or social profiles
    unenriched = sum(1 for l in leads if not getattr(l, "evidence", None))
    no_social = sum(1 for l in leads if not getattr(l, "social_discovery", None))
    if unenriched > 0 or no_social > 0:
        steps.append(add_step("ENRICH_LEADS", f"Enrich {unenriched + no_social} leads with evidence and social data"))

    # Step 5: Verify unverified leads
    unverified = sum(1 for l in leads if not getattr(l, "verification", None))
    if unverified > 0:
        steps.append(add_step("VERIFY_LEADS", f"Verify {unverified} unverified leads"))

    # Step 6: Score unscored leads
    unscored = sum(1 for l in leads if not getattr(l, "score_breakdown", None))
    if unscored > 0:
        steps.append(add_step("SCORE_LEADS", f"Score {unscored} unscored leads"))

    # Step 7: Draft outreach for verified, scored leads with no outreach
    ready = sum(
        1 for l in leads
        if getattr(l, "verification", None)
        and getattr(l, "score_breakdown", None)
        and (not getattr(l, "outreach_drafts", None) or len(l.outreach_drafts) == 0)
    )
    if ready > 0:
        steps.append(add_step("DRAFT_OUTREACH", f"Draft outreach for {ready} qualified leads"))

    # Step 8: Always end with user approval gate
    steps.append(add_step("AWAIT_USER_APPROVAL", "Review and approve next actions"))

    return AgentPlan(
        id=f"plan-{getattr(session, 'id', 'unknown')}-{int(now)}",
        campaign_id=getattr(session, "id", "unknown"),
        steps=steps,
        current_step=0,
        created_at=now,
        updated_at=now,
    )
