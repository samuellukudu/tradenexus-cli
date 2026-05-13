"""
tradenexus/session.py

Local JSON session persistence.
Sessions are saved to ~/.tradenexus/sessions/<id>.json
"""

from __future__ import annotations
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from .models import Lead, LeadStatus, MarketReport, ProductDetails, RegionSuggestion, StrategicContext

SESSIONS_DIR = Path.home() / ".tradenexus" / "sessions"


def _ensure_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def list_sessions() -> list[dict]:
    _ensure_dir()
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            sessions.append({
                "id": data.get("id"),
                "name": data.get("name", "Unnamed"),
                "product": data.get("product", {}).get("name", "?"),
                "created_at": data.get("created_at", 0),
                "leads_count": len(data.get("leads", [])),
            })
        except Exception:
            pass
    return sessions


def create_session(product: ProductDetails, name: Optional[str] = None) -> str:
    _ensure_dir()
    session_id = str(uuid.uuid4())[:8]
    data = {
        "id": session_id,
        "name": name or f"Session {session_id}",
        "created_at": time.time(),
        "product": product.to_dict(),
        "suggestions": [],
        "leads": [],
        "strategic_context": product.strategic_context.to_dict() if product.strategic_context else None,
    }
    _session_path(session_id).write_text(json.dumps(data, indent=2))
    return session_id


def load_session(session_id: str) -> dict:
    path = _session_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"Session '{session_id}' not found in {SESSIONS_DIR}")
    return json.loads(path.read_text())


def save_leads(session_id: str, leads: list[Lead]) -> None:
    data = load_session(session_id)
    data["leads"] = [lead.to_dict() for lead in leads]
    _session_path(session_id).write_text(json.dumps(data, indent=2))


def save_suggestions(session_id: str, suggestions: list[RegionSuggestion]) -> None:
    data = load_session(session_id)
    data["suggestions"] = [
        {"region": s.region, "reason": s.reason, "demandLevel": s.demand_level}
        for s in suggestions
    ]
    _session_path(session_id).write_text(json.dumps(data, indent=2))


def save_strategic_context(session_id: str, ctx: StrategicContext) -> None:
    data = load_session(session_id)
    data["strategic_context"] = ctx.to_dict()
    _session_path(session_id).write_text(json.dumps(data, indent=2))


def get_product_from_session(session_id: str) -> ProductDetails:
    data = load_session(session_id)
    product = ProductDetails.from_dict(data["product"])
    ctx = data.get("strategic_context")
    if ctx:
        product.strategic_context = StrategicContext.from_dict(ctx)
    return product


def export_leads_csv(session_id: str, output_path: str) -> None:
    import csv
    data = load_session(session_id)
    leads = data.get("leads", [])
    if not leads:
        raise ValueError("No leads in session to export.")
    fieldnames = list(leads[0].keys())
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)
