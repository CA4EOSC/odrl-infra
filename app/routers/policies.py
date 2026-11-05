from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Optional
import os
import json
import uuid
from pydantic import BaseModel, Field

from cli.create_policy import (
    ODRL_ACTIONS,
    COMMON_TARGET_ASSETS,
    COMMON_LEFT_OPERANDS,
    COMMON_OPERATORS,
    COMMON_DPV_PURPOSES,
    DUODRL_MAPPINGS,
    get_duo_preset,
    Validator,
    get_listing_4_2_preset,
    get_duo_0000042_preset,
    get_duo_0000024_preset,
    ODRL_CONTEXT,
    OAC_CONTEXT,
)
from ..services.oydid import run_oydid_command
from ..services.qdrant_service import qdrant_service
from ..services import cdif_vocab
from ..services.policy_metadata import stamp_policy_metadata

router = APIRouter(prefix="/policy", tags=["ODRL & OAC Policy Service"])


class ValidatePolicyRequest(BaseModel):
    policy: Dict[str, Any] = Field(..., description="ODRL Policy JSON-LD to validate")


class CreatePolicyApiRequest(BaseModel):
    policy: Dict[str, Any] = Field(..., description="ODRL Policy JSON-LD object to store / anchor")
    anchor_did: bool = Field(default=True, description="Whether to anchor policy into a DID")


@router.get("/vocab/actions")
async def get_vocab_actions():
    """Returns canonical W3C ODRL 2.2 Action Concepts with hierarchy and categories."""
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for action_name, meta in ODRL_ACTIONS.items():
        cat = meta["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "name": action_name,
            "iri": f"odrl:{action_name}",
            "description": meta["description"],
            "includedIn": meta["includedIn"]
        })
    return {
        "count": len(ODRL_ACTIONS),
        "actions": ODRL_ACTIONS,
        "categories": by_category
    }


@router.get("/vocab/helpers")
async def get_vocab_helpers():
    """Returns lists of target assets, operands, operators, DPV purposes, and DUODRL concepts for UI builders."""
    return {
        "target_assets": [{"iri": item[0], "label": item[1]} for item in COMMON_TARGET_ASSETS],
        "left_operands": [{"iri": item[0], "label": item[1]} for item in COMMON_LEFT_OPERANDS],
        "operators": [{"iri": item[0], "label": item[1]} for item in COMMON_OPERATORS],
        "dpv_purposes": [{"iri": item[0], "label": item[1]} for item in COMMON_DPV_PURPOSES],
        "duodrl_mappings": [
            {
                "id": k,
                "code": v["code"],
                "name": v["name"],
                "label": v["label"],
                "type": v["type"],
                "description": v["description"]
            }
            for k, v in DUODRL_MAPPINGS.items()
        ]
    }


@router.get("/vocab/cdif")
async def get_cdif_vocabularies():
    """Returns the CDIF access vocabularies (SKOS): CV1 actions, CV2 purposes, CV3 other constraints, CV4 duty actions."""
    return cdif_vocab.all_schemes()


@router.get("/vocab/cdif/{scheme}")
async def get_cdif_vocabulary(scheme: str):
    """Returns one CDIF vocabulary: cv1 (actions), cv2 (purposes), cv3 (other constraints) or cv4 (duty actions)."""
    if scheme not in cdif_vocab.SCHEMES:
        raise HTTPException(status_code=404, detail=f"Unknown vocabulary '{scheme}', use cv1, cv2, cv3 or cv4")
    return cdif_vocab.load_scheme(scheme)


PRESET_NAMES = ["listing-4.2", "read-only"] + [k.lower().replace("_", "-") for k in DUODRL_MAPPINGS]


def _as_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("@value") or value.get("@id") or "")
    if isinstance(value, list):
        return ", ".join(_as_text(v) for v in value)
    return "" if value is None else str(value)


def _policy_summary(policy: Dict[str, Any], uid: Optional[str], source: str, preset: Optional[str] = None) -> Dict[str, Any]:
    """Short description of a policy for the search list in the Policy Builder."""
    rules = [policy.get(k) or [] for k in ("odrl:permission", "permission", "odrl:prohibition", "prohibition")]
    targets = {_as_text(r.get("odrl:target") or r.get("target")) for group in rules for r in (group if isinstance(group, list) else [group]) if isinstance(r, dict)}
    return {
        "uid": uid or _as_text(policy.get("odrl:uid") or policy.get("uid") or policy.get("@id")),
        "source": source,  # "stored" (saved via /policy/create or /oac/policy) or "preset"
        "preset": preset,
        "type": _as_text(policy.get("@type") or policy.get("type")),
        "title": _as_text(policy.get("dcterms:title") or policy.get("rdfs:label")),
        "description": _as_text(policy.get("dcterms:description") or policy.get("skos:editorialNote")),
        "target": _as_text(policy.get("odrl:target") or policy.get("target")) or ", ".join(sorted(t for t in targets if t)),
        "creator": _as_text(policy.get("dcterms:creator")),
        "publisher": _as_text(policy.get("dcterms:publisher")),
        "version": _as_text(policy.get("owl:versionInfo")),
        "created": _as_text(policy.get("dcterms:created") or policy.get("dcterms:issued")),
        "policy": policy,
    }


def _matches(summary: Dict[str, Any], words: List[str]) -> bool:
    text = " ".join(str(v) for k, v in summary.items() if k != "policy").lower()
    # also search the rules (actions, purposes, constraint values)
    text += " " + json.dumps(summary["policy"], ensure_ascii=False).lower()
    return all(w in text for w in words)


@router.get("/existing")
async def list_existing_policies(
    q: str = "",
    include_presets: bool = True,
    limit: int = 50,
):
    """Existing policies for the Policy Builder search box: stored policies (Qdrant 'policy' collection)
    and the built-in presets. `q` keeps policies whose fields contain every word of the query."""
    summaries: List[Dict[str, Any]] = []
    stored_available = True
    try:
        for doc in qdrant_service.list_documents("policy"):
            summaries.append(_policy_summary(doc["json_ld"], doc["did"], "stored"))
    except Exception as e:
        print(f"Warning: could not list stored policies: {e}")
        stored_available = False
    # newest stored policies first
    summaries.sort(key=lambda s: s["created"], reverse=True)

    if include_presets:
        for name in PRESET_NAMES:
            summaries.append(_policy_summary(await get_preset(name), None, "preset", preset=name))

    words = q.lower().split()
    matches = [s for s in summaries if _matches(s, words)] if words else summaries
    return {
        "total": len(matches),
        "stored_available": stored_available,
        "results": matches[:limit],
    }


@router.get("/presets/{preset_name}")
async def get_preset(preset_name: str):
    """Returns pre-configured policy templates such as listing-4.2, duo-0000042, duo-0000024, or any DUODRL code."""
    # Check if preset is a DUO code directly (e.g. duo-0000004, DUO_0000043, etc.)
    normalized = preset_name.upper().replace("-", "_")
    if normalized in DUODRL_MAPPINGS:
        return get_duo_preset(normalized)

    if preset_name == "listing-4.2":
        return get_listing_4_2_preset()
    elif preset_name == "duo-0000042":
        return get_duo_0000042_preset()
    elif preset_name == "duo-0000024":
        return get_duo_0000024_preset()
    elif preset_name == "read-only":
        return {
            "@context": [ODRL_CONTEXT],
            "@type": "Set",
            "type": "Set",
            "odrl:uid": "urn:uuid:example-read-only",
            "dcterms:description": "Read-only access policy",
            "odrl:permission": [{"odrl:target": "http://example.com/asset:dataset", "odrl:action": "odrl:read"}],
            "odrl:prohibition": [{"odrl:target": "http://example.com/asset:dataset", "odrl:action": "odrl:modify"}],
        }
    raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")


@router.post("/validate")
async def validate_policy(request: ValidatePolicyRequest):
    """
    Validates an ODRL/OAC policy against structural rules, Pydantic models, and SHACL shapes.
    """
    is_valid, errors = Validator.validate_policy(request.policy)
    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": cdif_vocab.policy_warnings(request.policy),
    }


@router.post("/create")
async def create_policy(request: CreatePolicyApiRequest):
    """
    Validates and stores an ODRL/OAC Policy, optionally anchoring it as a DID and indexing in Qdrant.
    """
    policy = stamp_policy_metadata(request.policy)
    is_valid, errors = Validator.validate_policy(policy)
    if not is_valid:
        raise HTTPException(status_code=422, detail={"message": "Policy validation failed", "errors": errors})

    did = None
    if request.anchor_did:
        try:
            result = run_oydid_command(["create", "--json-output"], input_data=policy)
            if result.returncode == 0:
                did_data = json.loads(result.stdout)
                did = did_data.get("did")
                policy["odrl:uid"] = did
        except Exception as e:
            # Fallback if oydid is not in runtime path
            print(f"Warning: DID anchoring failed: {e}")

    # Fallback uid if did not generated
    if not did:
        did = policy.get("odrl:uid") or policy.get("uid") or f"urn:uuid:{uuid.uuid4()}"

    # Upsert to Qdrant collection if available
    try:
        qdrant_service.upsert_document(did, policy)
    except Exception as e:
        print(f"Warning: Failed to index in Qdrant: {e}")

    return {
        "status": "created",
        "uid": did,
        "policy": policy
    }

