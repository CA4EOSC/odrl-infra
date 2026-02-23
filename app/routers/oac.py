from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, List, Optional
from ..models_oac import OacPolicyCreateRequest
from ..services.oydid import run_oydid_command
from ..services.qdrant_service import qdrant_service
import json

router = APIRouter(prefix="/oac", tags=["ODRL Access Control Profile"])

@router.post("/policy")
async def create_oac_policy(policy: OacPolicyCreateRequest):
    """
    Create a new ODRL Access Control Policy (OAC) backed by a DID.
    The Policy content is stored as the DID Document (or payload).
    """
    try:
        # Prepare payload
        policy_dict = policy.dict(by_alias=True)
        
        # Use OYDID to create a DID with this policy as payload
        result = run_oydid_command(["create", "--json-output"], input_data=policy_dict)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"OYDID creation failed: {result.stderr}")
            
        did_data = json.loads(result.stdout)
        did = did_data.get("did")
        
        # Store in Qdrant (auto-routes to 'policy' collection)
        try:
            qdrant_service.upsert_document(did, policy_dict)
        except Exception as e:
            print(f"Warning: Failed to store in Qdrant: {e}")
            
        return {
            "status": "created",
            "uid": did,
            "policy": did_data.get("doc", policy_dict)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/policy/{uid}")
async def get_oac_policy(uid: str):
    """Retrieve an OAC policy by its UID (which is a DID)."""
    # Use OYDID to read the DID
    result = run_oydid_command(["read", uid, "--json-output"])
    
    if result.returncode != 0:
        raise HTTPException(status_code=404, detail=f"Policy not found: {result.stderr}")
        
    try:
        did_doc = json.loads(result.stdout)
        return did_doc.get("doc", {})
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to decode OYDID response")

@router.get("/search")
async def search_oac_policies(
    q: str, 
    collection: Optional[str] = Query(None, description="Qdrant collection to search in (policy, prompts, variables, croissant, dids)")
):
    """
    Search for DIDs in Qdrant based on keywords.
    Returns both DID and JSON-LD with similarity measure.
    """
    try:
        # Search across all collections if not provided
        results = qdrant_service.search_documents(q, collection=collection)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
