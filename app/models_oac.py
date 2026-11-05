from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Union, Literal, Dict, Any

# Enums and Constants
OAC_CONTEXT = "https://w3id.org/oac/context.json" # Placeholder context
ODRL_CONTEXT = "http://www.w3.org/ns/odrl.jsonld"

# Base Classes
class OacBaseModel(BaseModel):
    pass

# Constraints
class OacConstraint(OacBaseModel):
    leftOperand: str = Field(..., alias="odrl:leftOperand", description="The left operand of the constraint (e.g., oac:Purpose)")
    operator: str = Field(..., alias="odrl:operator", description="The operator (e.g., odrl:isA, odrl:eq)")
    rightOperand: Union[str, List[str]] = Field(..., alias="odrl:rightOperand", description="The right operand (e.g., dpv:ResearchAndDevelopment)")
    title: Optional[str] = Field(None, alias="dcterms:title")

    class Config:
        populate_by_name = True

# Action refinement and action models
class OacAction(OacBaseModel):
    value: Optional[str] = Field(None, alias="rdf:value", description="Action IRI (e.g. odrl:use, odrl:distribute)")
    id: Optional[str] = Field(None, alias="@id", description="Action IRI identifier")
    refinement: Optional[List[OacConstraint]] = Field(None, alias="odrl:refinement", description="Refinements constraining the action")

    class Config:
        populate_by_name = True

# Permissions
class OacPermission(OacBaseModel):
    assigner: Optional[str] = Field(None, alias="odrl:assigner", description="The entity assigning the permission")
    assignee: Optional[str] = Field(None, alias="odrl:assignee", description="The entity receiving the permission")
    target: Optional[str] = Field(None, alias="odrl:target", description="The target asset (inherited from policy if omitted)")
    action: Union[str, OacAction, Dict[str, Any]] = Field(..., alias="odrl:action", description="The action allowed (e.g., oac:Read or Action with refinement)")
    constraint: Optional[List[OacConstraint]] = Field(None, alias="odrl:constraint", description="Constraints / purposes on the permission")
    hasContext: Optional[str] = Field(None, alias="dpv:hasContext", description="DPV context (e.g., dpv:Optional)")

    class Config:
        populate_by_name = True

# Policies
class OacPolicy(OacBaseModel):
    context: Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]] = Field(default=[ODRL_CONTEXT], alias="@context")
    type: str = Field(..., alias="@type", description="Type of policy: Preference, Requirement, Offer, Request, Agreement, Set")
    uid: str = Field(..., alias="odrl:uid", description="Unique identifier for the policy")
    profile: Optional[str] = Field(default="oac:", alias="odrl:profile")
    description: Optional[str] = Field(None, alias="dcterms:description")
    creator: Optional[str] = Field(None, alias="dcterms:creator")
    publisher: Optional[str] = Field(None, alias="dcterms:publisher")
    target: Optional[Union[str, List[str]]] = Field(None, alias="odrl:target", description="Default policy target asset")
    assigner: Optional[str] = Field(None, alias="odrl:assigner", description="Default policy assigner entity")
    # System-generated on store (YYYY-MM-DD), see app/services/policy_metadata.py
    created: Optional[str] = Field(None, alias="dcterms:created")
    modified: Optional[str] = Field(None, alias="dcterms:modified")
    issued: Optional[str] = Field(None, alias="dcterms:issued")
    versionInfo: Optional[str] = Field(None, alias="owl:versionInfo", description="Policy version (owl:versionInfo, e.g. 1.0)")
    permission: Optional[List[OacPermission]] = Field(default=None, alias="odrl:permission")
    prohibition: Optional[List[Dict[str, Any]]] = Field(default=None, alias="odrl:prohibition")
    obligation: Optional[List[Dict[str, Any]]] = Field(default=None, alias="odrl:obligation")
    source: Optional[Union[str, List[str]]] = Field(None, alias="dcterms:source")
    label: Optional[str] = Field(None, alias="rdfs:label")
    exactMatch: Optional[Union[str, List[str]]] = Field(None, alias="skos:exactMatch")
    editorialNote: Optional[str] = Field(None, alias="skos:editorialNote")

    class Config:
        populate_by_name = True

# Specific Requests for Validation (simplified wrapper if needed, but OacPolicy handles the JSON-LD structure)
class OacPolicyCreateRequest(OacPolicy):
    pass
