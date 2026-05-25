"""IMF SDMX access using sdmx1, with optional MSAL authentication."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd
import sdmx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from trade_intel.cache_store import cache_get, cache_set, make_key
from trade_intel.rate_limit import throttle

DEFAULT_IMF_CLIENT_ID = "446ce2fa-88b1-436c-b8e6-94491ca4f6fb"
DEFAULT_IMF_AUTHORITY = (
    "https://imfprdb2c.b2clogin.com/"
    "imfprdb2c.onmicrosoft.com/b2c_1a_signin_aad_simple_user_journey/"
)
DEFAULT_IMF_SCOPE = (
    "https://imfprdb2c.onmicrosoft.com/"
    "4042e178-3e2f-4ff9-ac38-1276c901c13d/iData.Login"
)

logging.getLogger("sdmx").setLevel(logging.ERROR)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _coerce_label(value: Any) -> str:
    text = str(value).strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text.replace("'", '"'))
            if isinstance(parsed, dict):
                return str(parsed.get("en") or next(iter(parsed.values()), "")).strip()
        except json.JSONDecodeError:
            pass
    return text


def _coerce_item_name(item: Any) -> str:
    return _coerce_label(getattr(item, "name", item))


def _frame_from_pandasdmx(obj: Any) -> pd.DataFrame:
    if isinstance(obj, pd.Series):
        return obj.rename("value").reset_index()
    if isinstance(obj, pd.DataFrame):
        return obj.reset_index()
    if isinstance(obj, dict):
        try:
            return pd.concat(obj, names=["series"]).reset_index()
        except (TypeError, ValueError):
            return pd.DataFrame([obj])
    if isinstance(obj, list):
        return pd.DataFrame(obj)
    return pd.DataFrame(obj)


def _frame_from_cache(key: str) -> pd.DataFrame | None:
    cached = cache_get(key)
    if cached is None:
        return None
    try:
        return pd.DataFrame(cached)
    except (TypeError, ValueError):
        return None


def _frame_to_cache(key: str, df: pd.DataFrame) -> None:
    cache_set(key, json.loads(df.to_json(orient="records", date_format="iso")))


class IMFDataQuery(BaseModel):
    """Validated IMF SDMX dataset request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    dataset: str
    key: str | None = None
    start_period: str | int | None = None
    end_period: str | int | None = None
    extra_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("dataset")
    @classmethod
    def _validate_dataset(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("dataset is required")
        return value

    @field_validator("key")
    @classmethod
    def _validate_key(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    def request_params(self) -> dict[str, str | int]:
        params: dict[str, str | int] = {}
        if self.start_period is not None:
            params["startPeriod"] = self.start_period
        if self.end_period is not None:
            params["endPeriod"] = self.end_period
        for name, value in self.extra_params.items():
            if value != "":
                params[name] = value
        return params


class IMFAuthSettings(BaseModel):
    """Validated auth settings for protected IMF endpoints."""

    model_config = ConfigDict(str_strip_whitespace=True)

    access_token: str | None = None
    client_id: str = Field(default_factory=lambda: os.environ.get("IMF_API_CLIENT_ID", DEFAULT_IMF_CLIENT_ID))
    authority: str = Field(default_factory=lambda: os.environ.get("IMF_API_AUTHORITY", DEFAULT_IMF_AUTHORITY))
    scope: str = Field(default_factory=lambda: os.environ.get("IMF_API_SCOPE", DEFAULT_IMF_SCOPE))

    @field_validator("access_token")
    @classmethod
    def _validate_access_token(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("client_id", "authority", "scope")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("authentication settings must not be blank")
        return value


def build_auth_headers(
    *,
    interactive: bool = False,
    access_token: str | None = None,
    client_id: str | None = None,
    authority: str | None = None,
    scope: str | None = None,
) -> dict[str, str] | None:
    """
    Return Authorization headers for the IMF API.

    If ``interactive`` is false and no token is provided, public access is used.
    """

    settings = IMFAuthSettings(
        access_token=access_token or os.environ.get("IMF_API_ACCESS_TOKEN"),
        client_id=client_id or os.environ.get("IMF_API_CLIENT_ID", DEFAULT_IMF_CLIENT_ID),
        authority=authority or os.environ.get("IMF_API_AUTHORITY", DEFAULT_IMF_AUTHORITY),
        scope=scope or os.environ.get("IMF_API_SCOPE", DEFAULT_IMF_SCOPE),
    )
    if settings.access_token:
        return {"Authorization": f"Bearer {settings.access_token}"}
    if not interactive:
        return None

    try:
        from msal import PublicClientApplication
    except ImportError as exc:
        raise RuntimeError("msal is required for interactive IMF authentication") from exc

    app = PublicClientApplication(settings.client_id, authority=settings.authority)
    token = app.acquire_token_interactive(scopes=[settings.scope])
    if not token or "access_token" not in token:
        detail = ""
        if token:
            detail = str(token.get("error_description") or token.get("error") or "").strip()
        message = "Failed to acquire IMF access token"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)
    token_type = str(token.get("token_type") or "Bearer")
    return {"Authorization": f"{token_type} {token['access_token']}"}


def _client() -> sdmx.Client:
    return sdmx.Client("IMF_DATA")


def _get_structure_message(dataset: str, *, headers: dict[str, str] | None = None) -> Any:
    throttle()
    return _client().dataflow(dataset, headers=headers)


def _find_concept(msg: Any, concept_id: str) -> Any | None:
    for scheme in getattr(msg, "concept_scheme", {}).values():
        items = getattr(scheme, "items", {})
        if concept_id in items:
            return items[concept_id]
    return None


def _find_codelist_id(msg: Any, dim: Any) -> str | None:
    local_rep = getattr(dim, "local_representation", None)
    enum = getattr(local_rep, "enumerated", None) if local_rep is not None else None
    if enum is not None:
        return str(getattr(enum, "id", "")).strip() or None

    concept = _find_concept(msg, str(getattr(getattr(dim, "concept_identity", None), "id", "")).strip())
    if concept is None:
        return None
    for rep_name in ("core_representation", "local_representation"):
        rep = getattr(concept, rep_name, None)
        enum = getattr(rep, "enumerated", None) if rep is not None else None
        if enum is not None:
            return str(getattr(enum, "id", "")).strip() or None
    return None


def _dimension_options(msg: Any, codelist_id: str | None) -> list[dict[str, str]]:
    if not codelist_id:
        return []
    codelists = getattr(msg, "codelist", {}) or {}
    codelist = codelists.get(codelist_id) if hasattr(codelists, "get") else None
    if codelist is None:
        return []
    items = getattr(codelist, "items", {}) or {}
    options = [
        {"value": str(code), "label": _coerce_item_name(item)}
        for code, item in items.items()
    ]
    return sorted(options, key=lambda row: (row["label"].lower(), row["value"]))


def list_dataflows(*, headers: dict[str, str] | None = None, search: str | None = None) -> pd.DataFrame:
    """List IMF datasets (dataflows), optionally filtered by a search term."""

    search_text = _blank_to_none(search)
    cache_key = make_key("imf_dataflows", auth=bool(headers))
    cached = _frame_from_cache(cache_key)
    if cached is not None:
        out = cached
    else:
        throttle()
        msg = _client().dataflow(headers=headers)
        flows = getattr(msg, "dataflow", None)
        if flows:
            try:
                series = sdmx.to_pandas(flows)
                out = series.rename_axis("dataset").reset_index(name="name")
            except Exception:
                rows: list[dict[str, str]] = []
                for dataset, flow in flows.items():
                    rows.append(
                        {
                            "dataset": str(dataset),
                            "name": _coerce_label(getattr(flow, "name", "")),
                        }
                    )
                out = pd.DataFrame(rows)
        else:
            out = pd.DataFrame(columns=["dataset", "name"])
        out = out.fillna("").sort_values(["dataset", "name"]).reset_index(drop=True)
        _frame_to_cache(cache_key, out)
    if search_text and not out.empty:
        mask = out["dataset"].astype(str).str.contains(search_text, case=False, na=False)
        if "name" in out.columns:
            mask = mask | out["name"].astype(str).str.contains(search_text, case=False, na=False)
        out = out[mask].reset_index(drop=True)
    return out


def describe_dataflow(dataset: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Return a best-effort description of one IMF dataset."""

    dataset = dataset.strip()
    if not dataset:
        raise ValueError("dataset is required")
    msg = _get_structure_message(dataset, headers=headers)
    flows = getattr(msg, "dataflow", None) or {}
    flow = flows.get(dataset) if hasattr(flows, "get") else None
    if flow is None and hasattr(flows, "values"):
        flow = next(iter(flows.values()), None)
    structures = getattr(msg, "structure", None) or {}
    dsd = next(iter(structures.values()), None) if hasattr(structures, "values") else None
    dimensions: list[str] = []
    dimension_details: list[dict[str, Any]] = []
    if dsd is not None:
        dims = getattr(getattr(dsd, "dimensions", None), "components", None) or []
        for dim in dims:
            dim_id = str(getattr(dim, "id", "")).strip()
            if not dim_id:
                continue
            dimensions.append(dim_id)
            concept_id = str(getattr(getattr(dim, "concept_identity", None), "id", "")).strip() or dim_id
            codelist_id = _find_codelist_id(msg, dim)
            dimension_details.append(
                {
                    "id": dim_id,
                    "concept_id": concept_id,
                    "codelist_id": codelist_id,
                    "options": _dimension_options(msg, codelist_id),
                    "is_time": dim_id == "TIME_PERIOD",
                }
            )
    return {
        "dataset": dataset,
        "name": _coerce_label(getattr(flow, "name", "")) if flow is not None else "",
        "dimensions": dimensions,
        "dimension_details": dimension_details,
        "has_structure": bool(dsd is not None),
    }


def fetch_dataset(query: IMFDataQuery, *, headers: dict[str, str] | None = None) -> pd.DataFrame:
    """Fetch IMF SDMX data and return it as a pandas DataFrame."""

    params = query.request_params()
    cache_key = make_key(
        "imf_dataset",
        auth=bool(headers),
        dataset=query.dataset,
        key=query.key or "*",
        start=query.start_period,
        end=query.end_period,
        params=json.dumps(params, sort_keys=True),
    )
    cached = _frame_from_cache(cache_key)
    if cached is not None:
        out = cached
    else:
        throttle()
        msg = _client().data(
            query.dataset,
            key=query.key,
            params=params or {},
            headers=headers,
        )
        out = _frame_from_pandasdmx(sdmx.to_pandas(msg))
        _frame_to_cache(cache_key, out)

    # Always ensure clean types to avoid Arrow serialization issues
    for col in out.columns:
        if col == "value":
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = out[col].fillna("").astype(str)

    return out
