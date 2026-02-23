from pydantic import BaseModel
from typing import Dict, Any, Optional

class DidCreateRequest(BaseModel):
    payload: Dict[str, Any]
    collection: Optional[str] = None

class DidUpdateRequest(BaseModel):
    did: str
    payload: Dict[str, Any]

class VariableRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    unit: Optional[str] = ""
    context: Optional[Dict[str, Any]] = {}

class VariableUpdateRequest(VariableRequest):
    did: str

class Membership(BaseModel):
    member: str
    role: str

class GroupRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    members: Optional[list[Membership]] = []

class GroupUpdateRequest(GroupRequest):
    did: str

class CroissantRequest(BaseModel):
    url: Optional[str] = None
    description: Optional[str] = ""
    payload: Optional[Dict[str, Any]] = {}

class CroissantUpdateRequest(CroissantRequest):
    did: str

class GoogleVcRequest(BaseModel):
    token: str
    subject_did: str

class SshVcRequest(BaseModel):
    public_key: str
    signature: str
    subject_did: str
    username: Optional[str] = "oydid-user" # Principal for ssh-keygen -I

class GitHubVcRequest(BaseModel):
    token: str
    subject_did: str

class OrcidVcRequest(BaseModel):
    token: str
    orcid: str
    subject_did: str
