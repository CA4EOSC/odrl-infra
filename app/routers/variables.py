from fastapi import APIRouter, HTTPException
from ..models import VariableRequest, VariableUpdateRequest
from ..services.oydid import run_oydid_command
from ..services.qdrant_service import qdrant_service
import json
from datetime import datetime

router = APIRouter(prefix="/variables", tags=["Variables"])

@router.post("/create")
async def create_variable(request: VariableRequest):
    """Create a new Variable DID"""
    payload = {
        "type": "Variable",
        "name": request.name,
        "description": request.description,
        "unit": request.unit,
        "context": request.context,
        "timestamp": datetime.now().isoformat()
    }
    
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
async def update_variable(did: str, request: VariableRequest):
    """Update an existing Variable DID"""
    payload = {
        "type": "Variable",
        "name": request.name,
        "description": request.description,
        "unit": request.unit,
        "context": request.context,
        "timestamp": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    result = run_oydid_command(["update", did, "--json-output"], input_data=payload)
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=400, detail=f"Update failed: {error_detail}")
        
    try:
        did_data = json.loads(result.stdout)
        # Update in Qdrant as well
        try:
            qdrant_service.upsert_document(did, payload)
        except Exception as e:
            print(f"Warning: Failed to update in Qdrant: {e}")
            
        return did_data
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}
