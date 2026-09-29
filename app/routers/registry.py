from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

REGISTRY_FILE = "qdrant_storage/email_did_registry.json"

class RegistryEntry(BaseModel):
    email: str
    did: str

def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {}
    try:
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading registry: {e}")
        return {}

def save_registry(data):
    # Ensure directory exists
    os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
    try:
        with open(REGISTRY_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving registry: {e}")

@router.get("/registry/{email}")
async def get_did_by_email(email: str):
    registry = load_registry()
    if email in registry:
        return {"email": email, "did": registry[email]}
    raise HTTPException(status_code=404, detail="Email not found in registry")

@router.post("/registry")
async def save_did_for_email(entry: RegistryEntry):
    registry = load_registry()
    registry[entry.email] = entry.did
    save_registry(registry)
    return {"status": "success", "email": entry.email, "did": entry.did}
