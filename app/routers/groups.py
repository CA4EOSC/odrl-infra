from fastapi import APIRouter, HTTPException
from ..models import GroupRequest, GroupUpdateRequest
from ..services.oydid import run_oydid_command
from ..services.qdrant_service import qdrant_service
import json
from datetime import datetime

router = APIRouter(prefix="/groups", tags=["Groups"])

@router.post("/create")
async def create_group(request: GroupRequest):
    """Create a new Organization (Group) DID"""
    payload = {
        "@context": "http://www.w3.org/ns/org#",
        "type": "Organization",
        "name": request.name,
        "description": request.description,
        "hasMember": [
            {
                "type": "Membership",
                "member": m.member,
                "role": m.role
            } for m in request.members
        ],
        "timestamp": datetime.now().isoformat()
    }
    
    result = run_oydid_command(["create", "--json-output"], input_data=payload)
    
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"OYDID Error: {result.stderr}")
        
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

@router.put("/update/{did}")
async def update_group(did: str, request: GroupRequest):
    """Update an existing Organization (Group) DID"""
    payload = {
        "@context": "http://www.w3.org/ns/org#",
        "type": "Organization",
        "name": request.name,
        "description": request.description,
        "hasMember": [
            {
                "type": "Membership",
                "member": m.member,
                "role": m.role
            } for m in request.members
        ],
        "timestamp": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    result = run_oydid_command(["update", did, "--json-output"], input_data=payload)
    
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Update failed: {result.stderr}")
        
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
