from fastapi import APIRouter, HTTPException
from ..models import CroissantRequest, CroissantUpdateRequest
from ..services.oydid import run_oydid_command
from ..services.qdrant_service import qdrant_service
import json
import requests
from datetime import datetime

router = APIRouter(prefix="/croissants", tags=["Croissants"])

@router.post("/create")
async def create_croissant(request: CroissantRequest):
    """Create a new Croissant DID"""
    payload = {
        "type": "Croissant",
        "description": request.description,
        "timestamp": datetime.now().isoformat()
    }
    
    # If URL is provided, try to fetch JSON-LD
    if request.url:
        try:
            response = requests.get(request.url, timeout=15)
            response.raise_for_status()
            jsonld = response.json()
            # Merge JSON-LD into payload
            payload.update(jsonld)
            payload["url"] = request.url # Ensure URL is preserved if not in JSON-LD
        except Exception as e:
            print(f"Warning: Failed to fetch JSON-LD from {request.url}: {e}")
            payload["url"] = request.url
            
    # If a payload was provided directly, merge it
    if request.payload:
        payload.update(request.payload)

    result = run_oydid_command(["create", "--json-output"], input_data=payload)
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=400, detail=f"OYDID Error: {error_detail}")
        
    try:
        did_data = json.loads(result.stdout)
        did = did_data.get("did")
        
        # Store in Qdrant
        try:
            qdrant_service.upsert_document(did, payload)
        except Exception as e:
            print(f"Warning: Failed to store in Qdrant: {e}")
            
        return did_data
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}

@router.put("/{did}")
async def update_croissant(did: str, request: CroissantRequest):
    """Update an existing Croissant DID"""
    payload = {
        "type": "Croissant",
        "description": request.description,
        "payload": request.payload,
        "url": request.url,
        "timestamp": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    result = run_oydid_command(["update", did, "--json-output"], input_data=payload)
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=400, detail=f"Update failed: {error_detail}")
        
    try:
        did_data = json.loads(result.stdout)
        # Update in Qdrant
        try:
            qdrant_service.upsert_document(did, payload)
        except Exception as e:
            print(f"Warning: Failed to update in Qdrant: {e}")
            
        return did_data
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}
