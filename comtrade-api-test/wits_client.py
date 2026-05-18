"""HTTP client for World Bank WITS REST API."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

WITS_NS = "http://wits.worldbank.org"
BASE_URL = "https://wits.worldbank.org/API/V1"
USER_AGENT = "comtrade-api-test/1.0 (WITS API research)"


def _request(url: str, *, accept: str = "application/json") -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"WITS HTTP {exc.code} for {url}: {body}") from exc


def get_json(url: str) -> dict[str, Any]:
    raw = _request(url, accept="application/json")
    text = raw.decode("utf-8", errors="replace").strip()
    if not text or text.startswith("{}"):
        raise RuntimeError(f"WITS returned no JSON records for {url}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"WITS response is not JSON for {url}: {text[:200]}") from exc


def get_xml(url: str) -> ET.Element:
    raw = _request(url, accept="application/xml")
    return ET.fromstring(raw)


def xml_text(parent: ET.Element, tag: str) -> str:
    node = parent.find(f"{{{WITS_NS}}}{tag}")
    return (node.text or "").strip() if node is not None else ""
