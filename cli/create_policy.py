#!/usr/bin/env python3
"""
Interactive Command-Line Tool for Step-by-Step ODRL & OAC Policy Creation.
Based on:
- W3C ODRL Vocabulary & Action Concepts: https://www.w3.org/TR/odrl-vocab/#actionConcepts
- OAC (ODRL Access Control / DPV Profile) for Data Privacy & Permissions
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from cli.config import (
        ODRL_CONTEXT,
        OAC_CONTEXT,
        DUODRL_CONTEXT,
        ODRL_PREFIX,
        DUODRL_PREFIX,
        DUODRL_MAPPINGS,
    )
except ImportError:
    from config import (
        ODRL_CONTEXT,
        OAC_CONTEXT,
        DUODRL_CONTEXT,
        ODRL_PREFIX,
        DUODRL_PREFIX,
        DUODRL_MAPPINGS,
    )


class Validator:
    """
    Validates ODRL and OAC Policy dictionaries according to:
    - W3C ODRL 2.2 Core Specification (https://www.w3.org/TR/odrl-vocab/)
    - OAC (ODRL Access Control / DPV profile) specifications
    """

    ALLOWED_POLICY_TYPES = {
        "Set", "Offer", "Agreement", "Request", "Preference", "Requirement",
        "odrl:Set", "odrl:Offer", "odrl:Agreement", "odrl:Request"
    }

    @classmethod
    def validate_constraint(cls, constraint: Dict[str, Any], path: str = "constraint") -> List[str]:
        errors: List[str] = []
        left_op = constraint.get("odrl:leftOperand") or constraint.get("leftOperand")
        operator = constraint.get("odrl:operator") or constraint.get("operator")
        right_op = constraint.get("odrl:rightOperand") or constraint.get("rightOperand")

        if not left_op:
            errors.append(f"{path}: Missing leftOperand ('odrl:leftOperand').")
        if not operator:
            errors.append(f"{path}: Missing operator ('odrl:operator').")
        if right_op is None or right_op == "":
            errors.append(f"{path}: Missing rightOperand ('odrl:rightOperand').")

        return errors

    @classmethod
    def validate_rule(cls, rule: Dict[str, Any], rule_type: str, index: int) -> List[str]:
        errors: List[str] = []
        path = f"{rule_type}[{index}]"

        # Action is mandatory for all rules (permission, prohibition, duty)
        action = rule.get("odrl:action") or rule.get("action")
        if not action:
            errors.append(f"{path}: Missing required action ('odrl:action').")
        elif isinstance(action, dict):
            # Complex action with refinement
            action_val = action.get("rdf:value") or action.get("@id") or action.get("value")
            if not action_val:
                errors.append(f"{path}.action: Missing action value identifier ('rdf:value' or '@id').")
            refinements = action.get("odrl:refinement") or action.get("refinement")
            if refinements:
                if not isinstance(refinements, list):
                    errors.append(f"{path}.action.refinement: Must be a list of constraint objects.")
                else:
                    for r_idx, r in enumerate(refinements):
                        if not isinstance(r, dict):
                            errors.append(f"{path}.action.refinement[{r_idx}]: Refinement must be an object/dict.")
                        else:
                            errors.extend(cls.validate_constraint(r, f"{path}.action.refinement[{r_idx}]"))

        # Target can be defined on the rule or inherited from the policy root
        # If validating an isolated rule without context, target is optional if provided at policy level

        # Check constraints if present
        constraints = rule.get("odrl:constraint") or rule.get("constraint")
        if constraints:
            if not isinstance(constraints, list):
                errors.append(f"{path}.constraint: Must be a list of constraint objects.")
            else:
                for c_idx, c in enumerate(constraints):
                    if not isinstance(c, dict):
                        errors.append(f"{path}.constraint[{c_idx}]: Constraint must be an object/dict.")
                    else:
                        errors.extend(cls.validate_constraint(c, f"{path}.constraint[{c_idx}]"))

        # Check consequential duties if present
        duties = rule.get("odrl:duty") or rule.get("duty")
        if duties:
            if not isinstance(duties, list):
                errors.append(f"{path}.duty: Must be a list of duty objects.")
            else:
                for d_idx, d in enumerate(duties):
                    if not isinstance(d, dict):
                        errors.append(f"{path}.duty[{d_idx}]: Duty must be an object/dict.")
                    else:
                        errors.extend(cls.validate_rule(d, f"{path}.duty", d_idx))

        return errors

    @classmethod
    def validate_policy(cls, policy: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates the entire policy structure.
        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors: List[str] = []

        if not isinstance(policy, dict):
            return False, ["Root policy must be a JSON object / dict."]

        # 1. Check Context
        ctx = policy.get("@context")
        if not ctx:
            errors.append("Missing '@context' declaration (e.g. 'http://www.w3.org/ns/odrl.jsonld').")

        # 2. Check Type
        p_type = policy.get("@type") or policy.get("type")
        if not p_type:
            errors.append("Missing policy type ('@type' or 'type', e.g. 'Offer', 'Agreement', 'Set').")
        elif p_type not in cls.ALLOWED_POLICY_TYPES:
            errors.append(
                f"Unknown policy type '{p_type}'. Must be one of: {sorted(list(cls.ALLOWED_POLICY_TYPES))}."
            )

        # 3. Check UID
        uid = policy.get("odrl:uid") or policy.get("uid")
        if not uid:
            errors.append("Missing policy identifier ('odrl:uid' or 'uid').")

        # 4. Check Rules
        permissions = policy.get("odrl:permission") or policy.get("permission") or []
        prohibitions = policy.get("odrl:prohibition") or policy.get("prohibition") or []
        obligations = policy.get("odrl:obligation") or policy.get("obligation") or []

        has_rules = bool(permissions or prohibitions or obligations)
        if not has_rules:
            errors.append("Policy has no rules. Must define at least one permission, prohibition, or obligation.")

        for i, perm in enumerate(permissions):
            if isinstance(perm, dict):
                errors.extend(cls.validate_rule(perm, "odrl:permission", i))
            else:
                errors.append(f"odrl:permission[{i}]: Must be an object/dict.")

        for i, prohib in enumerate(prohibitions):
            if isinstance(prohib, dict):
                errors.extend(cls.validate_rule(prohib, "odrl:prohibition", i))
            else:
                errors.append(f"odrl:prohibition[{i}]: Must be an object/dict.")

        for i, oblig in enumerate(obligations):
            if isinstance(oblig, dict):
                errors.extend(cls.validate_rule(oblig, "odrl:obligation", i))
            else:
                errors.append(f"odrl:obligation[{i}]: Must be an object/dict.")

        # 5. Check compatibility with internal Pydantic backend model if available
        try:
            from app.models_oac import OacPolicyCreateRequest
            # If policy has permission, test Pydantic validation
            if permissions:
                OacPolicyCreateRequest(**policy)
        except ImportError:
            pass  # Backend model not in path when run standalone
        except Exception as e:
            errors.append(f"Internal Pydantic OacPolicy validation error: {str(e)}")

        # 6. SHACL Shape Verification (via RDF Graph if rdflib is available)
        try:
            shacl_errors = cls.validate_shacl(policy)
            errors.extend(shacl_errors)
        except Exception as e:
            # Non-blocking if SHACL engine is not installed
            pass

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def validate_shacl(cls, policy: Dict[str, Any], shape_path: str = "cli/shacl/odrl_shape.ttl") -> List[str]:
        """
        Validates the policy against the SHACL shape file.
        If pyshacl is installed, executes full W3C SHACL validation.
        Otherwise, verifies graph conformance using rdflib.
        """
        errors: List[str] = []
        try:
            import rdflib
            import os

            if not os.path.exists(shape_path):
                # Try relative to script directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                alt_path = os.path.join(script_dir, "shacl", "odrl_shape.ttl")
                if os.path.exists(alt_path):
                    shape_path = alt_path
                else:
                    return []

            # Check if pyshacl is available
            try:
                import pyshacl
                # Parse policy JSON-LD
                policy_copy = dict(policy)
                # Ensure local offline context mapping to avoid external HTTP 403 blocks
                policy_copy["@context"] = {
                    "odrl": "http://www.w3.org/ns/odrl/2/",
                    "oac": "https://w3id.org/oac/",
                    "dpv": "https://w3id.org/dpv#",
                    "dcterms": "http://purl.org/dc/terms/",
                    "xsd": "http://www.w3.org/2001/XMLSchema#",
                    "Offer": "odrl:Offer",
                    "Agreement": "odrl:Agreement",
                    "Set": "odrl:Set",
                    "Request": "odrl:Request",
                    "uid": {"@id": "odrl:uid", "@type": "@id"},
                    "permission": {"@id": "odrl:permission", "@type": "@id"},
                    "prohibition": {"@id": "odrl:prohibition", "@type": "@id"},
                    "obligation": {"@id": "odrl:obligation", "@type": "@id"},
                    "target": {"@id": "odrl:target", "@type": "@id"},
                    "action": {"@id": "odrl:action", "@type": "@id"},
                    "assigner": {"@id": "odrl:assigner", "@type": "@id"},
                    "assignee": {"@id": "odrl:assignee", "@type": "@id"},
                    "constraint": {"@id": "odrl:constraint", "@type": "@id"},
                    "leftOperand": {"@id": "odrl:leftOperand", "@type": "@id"},
                    "operator": {"@id": "odrl:operator", "@type": "@id"},
                    "rightOperand": {"@id": "odrl:rightOperand", "@type": "@id"},
                    "hasContext": {"@id": "dpv:hasContext", "@type": "@id"},
                    "title": "dcterms:title",
                    "description": "dcterms:description",
                    "creator": {"@id": "dcterms:creator", "@type": "@id"},
                    "issued": "dcterms:issued",
                    "source": {"@id": "dcterms:source", "@type": "@id"},
                    "refinement": {"@id": "odrl:refinement", "@type": "@id"},
                    "value": {"@id": "rdf:value", "@type": "@id"},
                    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                }
                data_graph = rdflib.Graph()
                data_graph.parse(data=json.dumps(policy_copy), format="json-ld")
                shape_graph = rdflib.Graph()
                shape_graph.parse(shape_path, format="turtle")

                conforms, results_graph, results_text = pyshacl.validate(
                    data_graph,
                    shacl_graph=shape_graph,
                    inference="rdfs",
                    abort_on_first=False,
                )
                if not conforms:
                    errors.append(f"SHACL Validation Violation:\n{results_text}")
            except ImportError:
                # pyshacl is not installed; verify shape file can load cleanly
                shape_graph = rdflib.Graph()
                shape_graph.parse(shape_path, format="turtle")
        except Exception as e:
            errors.append(f"SHACL Shape Error: {str(e)}")

        return errors

# Action concepts defined in W3C ODRL 2.2 Recommendation
# (https://www.w3.org/TR/odrl-vocab/#actionConcepts)
ODRL_ACTIONS: Dict[str, Dict[str, Any]] = {
    # Core ODRL & OAC
    "use": {
        "category": "Core & General Use",
        "description": "To use an Asset (foundational action).",
        "includedIn": None,
    },
    "read": {
        "category": "Core & General Use",
        "description": "To obtain data or text from the Asset for human or machine comprehension.",
        "includedIn": "use",
    },
    "display": {
        "category": "Core & General Use",
        "description": "To render the Asset visually on a screen or monitor.",
        "includedIn": "use",
    },
    "play": {
        "category": "Core & General Use",
        "description": "To render the Asset as time-based audio/visual content.",
        "includedIn": "use",
    },
    "present": {
        "category": "Core & General Use",
        "description": "To render an Asset to a public audience or perform it.",
        "includedIn": "use",
    },
    "preview": {
        "category": "Core & General Use",
        "description": "To provide a limited or sample representation of the Asset.",
        "includedIn": "use",
    },
    "print": {
        "category": "Core & General Use",
        "description": "To render the Asset on physical paper or hard copy.",
        "includedIn": "use",
    },
    "execute": {
        "category": "Execution & Software",
        "description": "To run the software code, program, or executable Asset.",
        "includedIn": "use",
    },
    "install": {
        "category": "Execution & Software",
        "description": "To load and setup the software Asset onto a storage/runtime environment.",
        "includedIn": "use",
    },
    "uninstall": {
        "category": "Execution & Software",
        "description": "To remove the software Asset from a storage or runtime environment.",
        "includedIn": "use",
    },
    "modify": {
        "category": "Transformation & Modification",
        "description": "To change or update the Asset without creating a derivative work.",
        "includedIn": "use",
    },
    "derive": {
        "category": "Transformation & Modification",
        "description": "To create a new derivative work based on the Asset.",
        "includedIn": "use",
    },
    "transform": {
        "category": "Transformation & Modification",
        "description": "To convert the structure or file format of the Asset.",
        "includedIn": "derive",
    },
    "translate": {
        "category": "Transformation & Modification",
        "description": "To translate the natural language text of the Asset into another language.",
        "includedIn": "derive",
    },
    "annotate": {
        "category": "Transformation & Modification",
        "description": "To add comments, notations, or metadata to the Asset.",
        "includedIn": "use",
    },
    "anonymize": {
        "category": "Transformation & Modification",
        "description": "To strip or mask identifying personal data from the Asset.",
        "includedIn": "use",
    },
    "aggregate": {
        "category": "Transformation & Modification",
        "description": "To combine the Asset with other assets to form a collection.",
        "includedIn": "use",
    },
    "extract": {
        "category": "Extraction & Reproduction",
        "description": "To extract a portion or excerpt from the Asset.",
        "includedIn": "reproduce",
    },
    "extractChar": {
        "category": "Extraction & Reproduction",
        "description": "To extract individual characters from the text Asset.",
        "includedIn": "extract",
    },
    "extractWord": {
        "category": "Extraction & Reproduction",
        "description": "To extract individual words from the text Asset.",
        "includedIn": "extract",
    },
    "extractPage": {
        "category": "Extraction & Reproduction",
        "description": "To extract pages from the paginated Asset.",
        "includedIn": "extract",
    },
    "copy": {
        "category": "Extraction & Reproduction",
        "description": "To duplicate or make an exact copy of the Asset.",
        "includedIn": "reproduce",
    },
    "reproduce": {
        "category": "Extraction & Reproduction",
        "description": "To reproduce or make copies of the Asset in any material form.",
        "includedIn": "use",
    },
    "digitize": {
        "category": "Extraction & Reproduction",
        "description": "To produce a digital representation of a physical/analogue asset.",
        "includedIn": "use",
    },
    "distribute": {
        "category": "Distribution & Sharing",
        "description": "To publish, supply, or disseminate the Asset to third parties.",
        "includedIn": "use",
    },
    "share": {
        "category": "Distribution & Sharing",
        "description": "To share the Asset with other parties informally.",
        "includedIn": "distribute",
    },
    "shareAlike": {
        "category": "Distribution & Sharing",
        "description": "To distribute derivative works only under the same or compatible license.",
        "includedIn": "distribute",
    },
    "adHocShare": {
        "category": "Distribution & Sharing",
        "description": "To share the Asset ad-hoc in close proximity or within a transient group.",
        "includedIn": "share",
    },
    "stream": {
        "category": "Distribution & Sharing",
        "description": "To transmit audio or video data continuously in real time.",
        "includedIn": "distribute",
    },
    "export": {
        "category": "Distribution & Sharing",
        "description": "To export the Asset or its data outside the current system boundaries.",
        "includedIn": "use",
    },
    "transfer": {
        "category": "Transfer & Commercial",
        "description": "To transfer the ownership of the Asset permanently to another party.",
        "includedIn": None,
    },
    "give": {
        "category": "Transfer & Commercial",
        "description": "To transfer ownership or rights of the Asset without compensation.",
        "includedIn": "transfer",
    },
    "sell": {
        "category": "Transfer & Commercial",
        "description": "To transfer ownership of the Asset in exchange for financial compensation.",
        "includedIn": "transfer",
    },
    "lease": {
        "category": "Transfer & Commercial",
        "description": "To grant temporary possession or use of the Asset under agreement.",
        "includedIn": "use",
    },
    "lend": {
        "category": "Transfer & Commercial",
        "description": "To temporarily loan the Asset with expectation of return without financial fee.",
        "includedIn": "use",
    },
    "license": {
        "category": "Transfer & Commercial",
        "description": "To grant permission or authorization for specified uses to third parties.",
        "includedIn": "use",
    },
    "commercialize": {
        "category": "Transfer & Commercial",
        "description": "To exploit the Asset directly or indirectly for financial/commercial gain.",
        "includedIn": "use",
    },
    "secondaryUse": {
        "category": "Transfer & Commercial",
        "description": "To use the Asset for purposes other than the primary purpose for which it was collected.",
        "includedIn": "use",
    },
    "concurrentUse": {
        "category": "Transfer & Commercial",
        "description": "To use the Asset concurrently across multiple systems, sessions, or devices.",
        "includedIn": "use",
    },
    "ensureExclusivity": {
        "category": "Transfer & Commercial",
        "description": "To guarantee that rights granted are exclusive to the party.",
        "includedIn": "use",
    },
    "attribute": {
        "category": "Duties & Obligations",
        "description": "To acknowledge and give attribution/credit to the author or copyright holder.",
        "includedIn": "use",
    },
    "compensate": {
        "category": "Duties & Obligations",
        "description": "To provide financial, credit, or other agreed compensation.",
        "includedIn": "use",
    },
    "inform": {
        "category": "Duties & Obligations",
        "description": "To notify or inform a party when specified events or usage occurs.",
        "includedIn": "use",
    },
    "obtainConsent": {
        "category": "Duties & Obligations",
        "description": "To request and obtain explicit consent from a party prior to action.",
        "includedIn": "use",
    },
    "acceptTracking": {
        "category": "Duties & Obligations",
        "description": "To agree to and accept that usage of the Asset is tracked/monitored.",
        "includedIn": "use",
    },
    "reviewPolicy": {
        "category": "Duties & Obligations",
        "description": "To review the applicable policy terms periodically.",
        "includedIn": "use",
    },
    "nextPolicy": {
        "category": "Duties & Obligations",
        "description": "To bind downstream parties to comply with a designated next policy.",
        "includedIn": "use",
    },
    "delete": {
        "category": "Lifecycle & Storage",
        "description": "To permanently delete, erase, or destroy the Asset.",
        "includedIn": "use",
    },
    "archive": {
        "category": "Lifecycle & Storage",
        "description": "To store the Asset in a long-term retention or archival repository.",
        "includedIn": "use",
    },
    "index": {
        "category": "Lifecycle & Storage",
        "description": "To index the Asset or add it to an index/catalog for discovery.",
        "includedIn": "use",
    },
    "attachPolicy": {
        "category": "Lifecycle & Storage",
        "description": "To bind or attach an ODRL policy directly to the Asset.",
        "includedIn": "use",
    },
    "attachSource": {
        "category": "Lifecycle & Storage",
        "description": "To attach source code or documentation to the Asset.",
        "includedIn": "use",
    },
    "watermark": {
        "category": "Lifecycle & Storage",
        "description": "To embed a digital watermark or visible identifier into the Asset.",
        "includedIn": "use",
    },
    "textToSpeech": {
        "category": "Core & General Use",
        "description": "To convert written textual data into synthesized spoken audio.",
        "includedIn": "use",
    },
}

# Common Target Asset Concepts (ODRL & OAC / DPV personal data categories)
COMMON_TARGET_ASSETS = [
    ("duodrl:TemplateDataset", "DUODRL: Template dataset asset for research use"),
    ("duodrl:ResultsOfStudies", "DUODRL: Research study results / derivative asset"),
    ("oac:Identifier", "OAC / DPV: Unique personal identifier data"),
    ("oac:Age", "OAC / DPV: Age or demographic date of birth"),
    ("oac:Behavioral", "OAC / DPV: Behavioral or usage activity data"),
    ("oac:Biometric", "OAC / DPV: Biometric or physiological characteristic"),
    ("oac:Location", "OAC / DPV: Geographic or device location data"),
    ("oac:Financial", "OAC / DPV: Financial, bank or billing information"),
    ("oac:Health", "OAC / DPV: Medical or health record data"),
    ("http://example.com/asset:001", "Generic Web / URI Asset"),
]

# Common Left Operands (ODRL & OAC)
COMMON_LEFT_OPERANDS = [
    ("oac:Purpose", "OAC: Data Processing Purpose (e.g. dpv:IdentityVerification, duodrl:GRU)"),
    ("odrl:purpose", "ODRL: Broad purpose specification"),
    ("odrl:dateTime", "ODRL: Point in time or ISO date"),
    ("odrl:timeInterval", "ODRL: Recurring or specific time interval"),
    ("odrl:spatial", "ODRL: Spatial or geographical boundary"),
    ("odrl:recipient", "ODRL: Authorized recipient party or role (e.g. duodrl:NonProfitOrganisation)"),
    ("odrl:count", "ODRL: Number of times an action can be executed"),
    ("odrl:payAmount", "ODRL: Monetary payment amount required"),
    ("odrl:fileFormat", "ODRL: Required or restricted file MIME type"),
    ("odrl:systemDevice", "ODRL: Permitted device or execution environment"),
]

# Common Operators (including OAC/ODRL operators like isA and isNotA)
COMMON_OPERATORS = [
    ("odrl:isA", "Is an instance of (class or vocabulary term)"),
    ("oac:isNotA", "Is NOT an instance of (negation / exclusion)"),
    ("odrl:eq", "Equal to"),
    ("odrl:neq", "Not equal to"),
    ("odrl:isAnyOf", "Matches any of given values / purposes"),
    ("odrl:isNoneOf", "Matches none of given values"),
    ("odrl:isPartOf", "Is part of"),
    ("odrl:lt", "Less than"),
    ("odrl:lteq", "Less than or equal to"),
    ("odrl:gt", "Greater than"),
    ("odrl:gteq", "Greater than or equal to"),
]

# Common Right Operands for Purpose (DPV & DUODRL - Data Privacy & Data Use Ontology)
COMMON_DPV_PURPOSES = [
    ("duodrl:GRU", "DUODRL: General Research Use for any research purpose (DUO:0000042)"),
    ("duodrl:HealthMedicalBiomedicalResearch", "DUODRL: Health / Medical / Biomedical Research (DUO:0000043)"),
    ("duodrl:TemplateDiseaseOrCondition", "DUODRL: Specific disease or syndrome restriction (DUO:0000026)"),
    ("duodrl:TemplateSpecificProject", "DUODRL: Specific designated research project (DUO:0000018)"),
    ("duodrl:NonProfitOrganisation", "DUODRL: Restricted to non-profit organizations (DUO:0000004)"),
    ("duodrl:TemplateStudyResultsPublicationDate", "DUODRL: Publication moratorium release timestamp (DUO:0000024)"),
    ("dpv:IdentityVerification", "DPV: Purpose to verify user/subject identity"),
    ("dpv:CommercialResearch", "DPV: Commercial research and product development"),
    ("dpv:AcademicResearch", "DPV: Non-commercial academic research"),
    ("dpv:ServiceProvision", "DPV: Provision of requested service"),
    ("dpv:AccountManagement", "DPV: User account administration"),
    ("dpv:Marketing", "DPV: Direct or behavioral marketing"),
]


def prompt_input(prompt: str, default: Optional[str] = None, allow_empty: bool = True) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        try:
            val = input(f"{prompt}{suffix}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted by user.")
            sys.exit(0)
        if not val and default is not None:
            return default
        if not val and not allow_empty:
            print("  This field cannot be empty. Please enter a value.")
            continue
        return val


def prompt_choice(prompt: str, options: List[str], default_idx: int = 0) -> str:
    print(f"\n{prompt}")
    for idx, opt in enumerate(options, 1):
        indicator = " (default)" if (idx - 1) == default_idx else ""
        print(f"  [{idx}] {opt}{indicator}")
    while True:
        try:
            choice = input(f"Choose option [1-{len(options)}] [{default_idx + 1}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted by user.")
            sys.exit(0)
        if not choice:
            return options[default_idx]
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print(f"Invalid selection. Please enter a number between 1 and {len(options)}.")


def select_action() -> str:
    # Common quick actions including OAC profile
    quick_actions = [
        "oac:Read (OAC Privacy Access)",
        "odrl:read (W3C ODRL Read)",
        "odrl:use (General Use)",
        "odrl:distribute (Distribution)",
        "odrl:modify (Modification)",
        "odrl:derive (Derived works)",
        "Browse / Search all 54 W3C actions",
        "Enter custom action",
    ]
    quick_choice = prompt_choice("Select Action:", quick_actions, default_idx=0)
    if quick_choice.startswith("oac:Read"):
        return "oac:Read"
    elif quick_choice.startswith("odrl:read"):
        return "odrl:read"
    elif quick_choice.startswith("odrl:use"):
        return "odrl:use"
    elif quick_choice.startswith("odrl:distribute"):
        return "odrl:distribute"
    elif quick_choice.startswith("odrl:modify"):
        return "odrl:modify"
    elif quick_choice.startswith("odrl:derive"):
        return "odrl:derive"
    elif quick_choice == "Enter custom action":
        custom = prompt_input("Enter action IRI/name (e.g. oac:Read or odrl:read)", default="oac:Read", allow_empty=False)
        return custom

    # Browse / Search full W3C vocabulary
    categories = sorted(list({v["category"] for v in ODRL_ACTIONS.values()}))
    browse_modes = ["Search by keyword", "Browse by category"]
    b_mode = prompt_choice("Browse W3C Action Concepts:", browse_modes, default_idx=0)

    if b_mode == "Browse by category":
        chosen_cat = prompt_choice("Select category:", categories, default_idx=0)
        cat_actions = [k for k, v in ODRL_ACTIONS.items() if v["category"] == chosen_cat]
        cat_actions.sort()
        labels = [f"{act} - {ODRL_ACTIONS[act]['description']}" for act in cat_actions]
        chosen = prompt_choice(f"Actions in {chosen_cat}:", labels, default_idx=0)
        act_name = chosen.split(" - ")[0]
        return f"{ODRL_PREFIX}{act_name}"
    else:
        while True:
            kw = prompt_input("Enter keyword search (or 'all')", default="read").lower()
            matches = [
                k for k, v in ODRL_ACTIONS.items()
                if kw == "all" or kw in k.lower() or kw in v["description"].lower()
            ]
            if not matches:
                print(f"No match for '{kw}'. Try again.")
                continue
            labels = [f"{k} - {ODRL_ACTIONS[k]['description']}" for k in matches]
            chosen = prompt_choice(f"Matches for '{kw}':", labels, default_idx=0)
            act_name = chosen.split(" - ")[0]
            return f"{ODRL_PREFIX}{act_name}"


def select_target() -> str:
    target_options = [f"{name} ({desc})" for name, desc in COMMON_TARGET_ASSETS] + ["Custom target URI / identifier"]
    choice = prompt_choice("Select Target Asset:", target_options, default_idx=0)
    if choice == "Custom target URI / identifier":
        return prompt_input("Enter custom target URI/name (e.g., oac:Identifier, did:..., https://...)", allow_empty=False)
    return choice.split(" ")[0]


def create_constraints() -> List[Dict[str, Any]]:
    constraints: List[Dict[str, Any]] = []
    print("\n--- Constraints (e.g. Purpose, Spatial, Temporal) ---")
    add_any = prompt_choice("Do you want to add constraints to this rule?", ["Add a constraint", "No constraints"], default_idx=0)
    if add_any == "No constraints":
        return constraints

    while True:
        # Constraint Title (dcterms:title) as seen in Listing 4.2
        title = prompt_input("Constraint Title/Description [optional, e.g., 'Purpose for access is to verify identity']", default="")

        # Left Operand
        left_op_options = [f"{op} - {desc}" for op, desc in COMMON_LEFT_OPERANDS] + ["Custom left operand"]
        left_choice = prompt_choice("Select Left Operand:", left_op_options, default_idx=0)
        if left_choice == "Custom left operand":
            left_op = prompt_input("Enter custom left operand (e.g. oac:Purpose, odrl:purpose)", default="oac:Purpose", allow_empty=False)
        else:
            left_op = left_choice.split(" - ")[0]

        # Operator (odrl:isA, oac:isNotA, odrl:eq, etc.)
        op_options = [f"{op} - {desc}" for op, desc in COMMON_OPERATORS] + ["Custom operator"]
        op_choice = prompt_choice("Select Operator:", op_options, default_idx=0)
        if op_choice == "Custom operator":
            operator = prompt_input("Enter operator (e.g. odrl:isA, oac:isNotA, odrl:eq)", default="odrl:isA", allow_empty=False)
        else:
            operator = op_choice.split(" - ")[0]

        # Right Operand (e.g. dpv:IdentityVerification, dpv:CommercialResearch)
        if "Purpose" in left_op or "purpose" in left_op:
            dpv_options = [f"{dpv} - {desc}" for dpv, desc in COMMON_DPV_PURPOSES] + ["Custom right operand"]
            dpv_choice = prompt_choice("Select Right Operand (DPV Purpose):", dpv_options, default_idx=0)
            if dpv_choice == "Custom right operand":
                right_op = prompt_input("Enter purpose / right operand", default="dpv:IdentityVerification", allow_empty=False)
            else:
                right_op = dpv_choice.split(" - ")[0]
        else:
            right_op = prompt_input("Enter Right Operand value", allow_empty=False)

        constraint: Dict[str, Any] = {
            "odrl:leftOperand": left_op,
            "odrl:operator": operator,
            "odrl:rightOperand": right_op,
        }
        if title:
            constraint["dcterms:title"] = title

        constraints.append(constraint)
        print(f"  Added Constraint: {left_op} {operator} {right_op} ({title if title else 'No title'})")

        more = prompt_choice("Add another constraint to this rule?", ["No", "Yes"], default_idx=0)
        if more == "No":
            break

    return constraints


def configure_permission_rule(default_assigner: Optional[str] = None) -> Dict[str, Any]:
    """
    Configures an ODRL/OAC Permission rule based on Listing 4.2:
    - dpv:hasContext (dpv:Required, dpv:Optional)
    - odrl:assigner
    - odrl:assignee
    - odrl:action (e.g. oac:Read, odrl:read)
    - odrl:target (e.g. oac:Identifier, oac:Age)
    - odrl:constraint (odrl:leftOperand, odrl:operator, odrl:rightOperand, dcterms:title)
    """
    print("\n" + "=" * 55)
    print("      Configuring PERMISSION Rule")
    print("=" * 55)

    # 1. DPV Context: dpv:hasContext (e.g. dpv:Required, dpv:Optional)
    context_options = [
        "dpv:Required (Consent/Processing is strictly required)",
        "dpv:Optional (Consent/Processing is optional/secondary)",
        "None (Standard ODRL permission without DPV context)",
    ]
    ctx_choice = prompt_choice("Select Permission Context (dpv:hasContext):", context_options, default_idx=0)
    has_context = None
    if ctx_choice.startswith("dpv:Required"):
        has_context = "dpv:Required"
    elif ctx_choice.startswith("dpv:Optional"):
        has_context = "dpv:Optional"

    # 2. Assigner (Entity granting the permission)
    assigner = prompt_input(
        "Assigner (odrl:assigner: e.g. DID or WebID https://solidweb.me/.../card#me)",
        default=default_assigner if default_assigner else "",
    )

    # 3. Assignee (Entity receiving permission - optional)
    assignee = prompt_input("Assignee (odrl:assignee: receiver DID or WebID) [optional]", default="")

    # 4. Action (e.g. oac:Read, odrl:read, etc.)
    action = select_action()
    print(f"Action set to: {action}")

    # 5. Target Asset (e.g. oac:Identifier, oac:Age, URI)
    target = select_target()
    print(f"Target set to: {target}")

    rule: Dict[str, Any] = {
        "odrl:target": target,
        "odrl:action": action,
    }
    if has_context:
        rule["dpv:hasContext"] = has_context
    if assigner:
        rule["odrl:assigner"] = assigner
    if assignee:
        rule["odrl:assignee"] = assignee

    # 6. Constraints (with title, leftOperand, operator, rightOperand)
    constraints = create_constraints()
    if constraints:
        rule["odrl:constraint"] = constraints

    # 7. Optional Consequential Duty
    add_duty = prompt_choice("Does this permission carry a consequential Duty/Obligation?", ["No", "Yes"], default_idx=0)
    if add_duty == "Yes":
        duty_action = select_action()
        rule["odrl:duty"] = [{"odrl:action": duty_action}]

    return rule


def interactive_policy_builder() -> Dict[str, Any]:
    print("=" * 70)
    print("   W3C ODRL & OAC Policy Creator (Interactive Step-by-Step CLI)")
    print("   Reference: Listing 4.2 ODRL/OAC Offer & W3C Action Concepts")
    print("=" * 70)

    policy_types = [
        "Offer (Listing 4.2: odrl:Offer issued by assigner)",
        "Agreement (Bilateral agreement between assigner and assignee)",
        "Set (General policy definition)",
        "Request (odrl:Request by client/consumer)",
        "Preference (Subject privacy preference)",
        "Requirement (Required conditions specification)",
    ]
    p_type_choice = prompt_choice("Step 1: Select Policy Type (@type):", policy_types, default_idx=0)
    policy_type = p_type_choice.split(" ")[0]

    # Policy UID
    default_uid = f"urn:uuid:{uuid.uuid4()}"
    uid = prompt_input("Step 2: Enter Unique Policy Identifier (odrl:uid)", default=default_uid, allow_empty=False)

    # Profile (Listing 4.2 uses 'oac:')
    profile_choices = [
        "oac: (ODRL Access Control / Privacy Profile)",
        "http://www.w3.org/ns/odrl/2/ (Core ODRL)",
        "Custom profile",
    ]
    profile_choice = prompt_choice("Step 3: Select Policy Profile (odrl:profile):", profile_choices, default_idx=0)
    if profile_choice.startswith("oac:"):
        profile = "oac:"
    elif profile_choice.startswith("http"):
        profile = "http://www.w3.org/ns/odrl/2/"
    else:
        profile = prompt_input("Enter custom profile", default="oac:", allow_empty=False)

    # Description (dcterms:description)
    description = prompt_input(
        "Step 4: Policy Description (dcterms:description)",
        default="Offer to read identifier data for identity verification and age data if purpose is not commercial research.",
    )

    # Creator (dcterms:creator)
    creator = prompt_input(
        "Step 5: Creator Identifier (dcterms:creator: WebID or DID)",
        default="https://solidweb.me/besteves4/profile/card#me",
    )

    # Source (dcterms:source)
    source_input = prompt_input(
        "Step 6: Policy Source(s) (dcterms:source, comma-separated URIs) [optional]",
        default="https://solidweb.me/besteves4/policies/requirement1, https://solidweb.me/besteves4/policies/preference1",
    )
    sources = [s.strip() for s in source_input.split(",") if s.strip()] if source_input else []

    issued = datetime.now(timezone.utc).isoformat()

    policy: Dict[str, Any] = {
        "@context": [ODRL_CONTEXT, OAC_CONTEXT] if profile == "oac:" else [ODRL_CONTEXT],
        "@type": policy_type,
        "type": policy_type,
        "odrl:uid": uid,
        "odrl:profile": profile,
        "dcterms:issued": issued,
    }
    if description:
        policy["dcterms:description"] = description
    if creator:
        policy["dcterms:creator"] = creator
    if sources:
        policy["dcterms:source"] = sources if len(sources) > 1 else sources[0]

    permissions: List[Dict[str, Any]] = []
    prohibitions: List[Dict[str, Any]] = []
    obligations: List[Dict[str, Any]] = []

    print("\nStep 7: Configure Policy Rules (Permissions / Prohibitions / Duties)")
    while True:
        rule_kind = prompt_choice(
            "Select rule kind to add:",
            [
                "Permission (Listing 4.2 style permission with DPV context & constraints)",
                "Prohibition (Forbidden action)",
                "Duty / Obligation (Required action)",
                "Done adding rules (Review & Generate)",
            ],
            default_idx=0 if not permissions else 3,
        )

        if rule_kind.startswith("Done"):
            if not permissions and not prohibitions and not obligations:
                print("Notice: Policy currently has no rules.")
                finish = prompt_choice("Proceed without rules?", ["Add a rule", "Proceed anyway"], default_idx=0)
                if finish == "Add a rule":
                    continue
            break

        if rule_kind.startswith("Permission"):
            perm_rule = configure_permission_rule(default_assigner=creator)
            permissions.append(perm_rule)

        elif rule_kind.startswith("Prohibition"):
            print("\nConfiguring Prohibition Rule:")
            act = select_action()
            tgt = select_target()
            rule = {"odrl:target": tgt, "odrl:action": act}
            if creator:
                rule["odrl:assigner"] = creator
            
            output_asset = prompt_input("Output Asset affected (odrl:output, e.g. duodrl:ResultsOfStudies) [optional]", default="")
            if output_asset:
                rule["odrl:output"] = output_asset

            constraints = create_constraints()
            if constraints:
                rule["odrl:constraint"] = constraints

            prohibitions.append(rule)

        elif rule_kind.startswith("Duty"):
            print("\nConfiguring Duty Rule:")
            act = select_action()
            rule = {"odrl:action": act}
            obligations.append(rule)

    if permissions:
        policy["odrl:permission"] = permissions
    if prohibitions:
        policy["odrl:prohibition"] = prohibitions
    if obligations:
        policy["odrl:obligation"] = obligations

    return policy


def get_duo_preset(duo_id: str) -> Dict[str, Any]:
    """Generates an ODRL policy from any standard DUODRL mapping concept."""
    clean_id = duo_id.replace("DUO:", "DUO_").replace("obo:", "")
    if clean_id not in DUODRL_MAPPINGS:
        raise ValueError(f"Unknown DUO concept {duo_id}")

    mapping = DUODRL_MAPPINGS[clean_id]
    rule_type = mapping["type"]
    policy_uid = f"duodrl:{clean_id}"

    constraint = {
        "odrl:leftOperand": mapping["operand"],
        "odrl:operator": mapping["operator"],
        "odrl:rightOperand": mapping["value"],
    }

    rule = {
        "odrl:target": mapping["target"],
        "odrl:action": mapping["action"],
        "odrl:constraint": [constraint],
    }
    if mapping.get("output"):
        rule["odrl:output"] = mapping["output"]

    policy: Dict[str, Any] = {
        "@context": [
            ODRL_CONTEXT,
            OAC_CONTEXT,
            {
                "duodrl": "https://w3id.org/duodrl#",
                "obo": "http://purl.obolibrary.org/obo/",
                "skos": "http://www.w3.org/2004/02/skos/core#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            },
        ],
        "@type": "Set",
        "type": "Set",
        "odrl:uid": policy_uid,
        "odrl:profile": "https://w3id.org/duodrl#",
        "rdfs:label": f"{clean_id}: {mapping['label']} ({mapping['name']})",
        "skos:exactMatch": mapping["code"],
        "skos:editorialNote": mapping["description"],
    }

    if rule_type == "Permission":
        policy["odrl:permission"] = [rule]
    elif rule_type == "Prohibition":
        policy["odrl:prohibition"] = [rule]
    elif rule_type == "Duty":
        policy["odrl:obligation"] = [rule]

    return policy


def get_duo_0000042_preset() -> Dict[str, Any]:
    """Returns DUO_0000042 (General Research Use) ODRL Set Policy."""
    return get_duo_preset("DUO_0000042")


def get_duo_0000024_preset() -> Dict[str, Any]:
    """Returns DUO_0000024 (Publication Moratorium) ODRL Set Policy."""
    return get_duo_preset("DUO_0000024")


def get_listing_4_2_preset() -> Dict[str, Any]:
    """Returns exact ODRL offer from Listing 4.2 in the screenshot."""
    creator_uri = "https://solidweb.me/besteves4/profile/card#me"
    policy_uri = "https://solidweb.me/besteves4/policies/offer1"
    return {
        "@context": [ODRL_CONTEXT, OAC_CONTEXT],
        "@type": "Offer",
        "type": "Offer",
        "odrl:uid": policy_uri,
        "odrl:profile": "oac:",
        "dcterms:description": "Offer to read identifier data for identity verification and age data if purpose is not commercial research.",
        "dcterms:creator": creator_uri,
        "dcterms:source": [
            "https://solidweb.me/besteves4/policies/requirement1",
            "https://solidweb.me/besteves4/policies/preference1",
        ],
        "dcterms:issued": "2023-10-20T22:15:34Z",
        "odrl:permission": [
            {
                "dpv:hasContext": "dpv:Required",
                "odrl:assigner": creator_uri,
                "odrl:action": "oac:Read",
                "odrl:target": "oac:Identifier",
                "odrl:constraint": [
                    {
                        "dcterms:title": "Purpose for access is to verify the identity of the assigner.",
                        "odrl:leftOperand": "oac:Purpose",
                        "odrl:operator": "odrl:isA",
                        "odrl:rightOperand": "dpv:IdentityVerification",
                    }
                ],
            },
            {
                "dpv:hasContext": "dpv:Optional",
                "odrl:assigner": creator_uri,
                "odrl:action": "oac:Read",
                "odrl:target": "oac:Age",
                "odrl:constraint": [
                    {
                        "dcterms:title": "Purpose for access is not commercial research.",
                        "odrl:leftOperand": "oac:Purpose",
                        "odrl:operator": "oac:isNotA",
                        "odrl:rightOperand": "dpv:CommercialResearch",
                    }
                ],
            },
        ],
    }


def list_actions_summary():
    print(f"\nW3C ODRL 2.2 Action Concepts ({len(ODRL_ACTIONS)} canonical actions)")
    print("=" * 80)
    by_cat: Dict[str, List[str]] = {}
    for act, data in ODRL_ACTIONS.items():
        by_cat.setdefault(data["category"], []).append(act)

    for cat in sorted(by_cat.keys()):
        print(f"\n[{cat.upper()}]")
        for act in sorted(by_cat[cat]):
            desc = ODRL_ACTIONS[act]["description"]
            inc = f" (includedIn: {ODRL_ACTIONS[act]['includedIn']})" if ODRL_ACTIONS[act]["includedIn"] else ""
            print(f"  • odrl:{act}{inc}")
            print(f"      {desc}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive CLI tool for step-by-step ODRL/OAC policy creation based on W3C Action Concepts & Listing 4.2."
    )
    parser.add_argument("-o", "--output", help="Save the generated policy JSON to specified file path.")
    parser.add_argument("--list-actions", action="store_true", help="Print all standard W3C ODRL action concepts and exit.")
    parser.add_argument(
        "--quick-preset",
        choices=[
            "duo-0000042",
            "duo-0000024",
            "listing-4.2",
            "read-only",
            "cc-by-attribution",
            "commercial-forbidden",
            "ai-training-permission",
        ],
        help="Quickly generate a standard pre-configured ODRL policy template (e.g. duo-0000042, duo-0000024, listing-4.2).",
    )
    args = parser.parse_args()

    if args.list_actions:
        list_actions_summary()
        sys.exit(0)

    if args.quick_preset:
        policy_uid = f"urn:uuid:{uuid.uuid4()}"
        if args.quick_preset == "duo-0000042":
            policy = get_duo_0000042_preset()
        elif args.quick_preset == "duo-0000024":
            policy = get_duo_0000024_preset()
        elif args.quick_preset == "listing-4.2":
            policy = get_listing_4_2_preset()
        elif args.quick_preset == "read-only":
            policy = {
                "@context": [ODRL_CONTEXT],
                "@type": "Set",
                "odrl:uid": policy_uid,
                "dcterms:description": "Read-only access policy",
                "odrl:permission": [{"odrl:target": "http://example.com/asset:dataset", "odrl:action": "odrl:read"}],
                "odrl:prohibition": [{"odrl:target": "http://example.com/asset:dataset", "odrl:action": "odrl:modify"}],
            }
        elif args.quick_preset == "cc-by-attribution":
            policy = {
                "@context": [ODRL_CONTEXT],
                "@type": "Offer",
                "odrl:uid": policy_uid,
                "dcterms:description": "Open access with attribution requirement (CC-BY equivalent)",
                "odrl:permission": [
                    {
                        "odrl:target": "http://example.com/asset:content",
                        "odrl:action": "odrl:distribute",
                        "odrl:duty": [{"odrl:action": "odrl:attribute"}],
                    },
                    {
                        "odrl:target": "http://example.com/asset:content",
                        "odrl:action": "odrl:derive",
                        "odrl:duty": [{"odrl:action": "odrl:attribute"}],
                    },
                ],
            }
        elif args.quick_preset == "commercial-forbidden":
            policy = {
                "@context": [ODRL_CONTEXT],
                "@type": "Set",
                "odrl:uid": policy_uid,
                "dcterms:description": "Educational/Research only, commercial use prohibited",
                "odrl:permission": [
                    {
                        "odrl:target": "http://example.com/asset:resource",
                        "odrl:action": "odrl:read",
                        "odrl:constraint": [
                            {"leftOperand": "odrl:purpose", "operator": "odrl:eq", "rightOperand": "ResearchAndEducation"}
                        ],
                    }
                ],
                "odrl:prohibition": [{"odrl:target": "http://example.com/asset:resource", "odrl:action": "odrl:commercialize"}],
            }
        elif args.quick_preset == "ai-training-permission":
            policy = {
                "@context": [ODRL_CONTEXT, OAC_CONTEXT],
                "@type": "Agreement",
                "odrl:uid": policy_uid,
                "odrl:profile": "oac:",
                "dcterms:description": "Explicit authorization for AI model training and evaluation",
                "odrl:permission": [
                    {
                        "dpv:hasContext": "dpv:Required",
                        "odrl:target": "http://example.com/asset:corpus",
                        "odrl:action": "odrl:derive",
                        "odrl:constraint": [
                            {"leftOperand": "oac:Purpose", "operator": "odrl:isA", "rightOperand": "ModelTraining"}
                        ],
                    },
                    {
                        "dpv:hasContext": "dpv:Optional",
                        "odrl:target": "http://example.com/asset:corpus",
                        "odrl:action": "oac:Read",
                    },
                ],
                "odrl:prohibition": [
                    {"odrl:target": "http://example.com/asset:corpus", "odrl:action": "odrl:distribute"}
                ],
            }
    else:
        policy = interactive_policy_builder()

    policy_json = json.dumps(policy, indent=2)
    print("\n" + "=" * 70)
    print(" Generated W3C ODRL / OAC Policy JSON-LD:")
    print("=" * 70)
    print(policy_json)

    # Validate generated policy with Validator
    print("\n" + "-" * 70)
    print(" Validating Policy against ODRL 2.2 / OAC Specifications...")
    print("-" * 70)
    is_valid, validation_errors = Validator.validate_policy(policy)
    if is_valid:
        print(" Policy Validation PASSED: Conformant with ODRL 2.2 & OAC model.")
    else:
        print(" Policy Validation FAILED:")
        for err in validation_errors:
            print(f"   - {err}")

    output_path = args.output
    if not output_path and not args.quick_preset:
        save_prompt = prompt_choice("\nWould you like to save this policy to a file?", ["Yes", "No"], default_idx=0)
        if save_prompt == "Yes":
            output_path = prompt_input("Enter filename to save", default="odrl_policy.json", allow_empty=False)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(policy_json)
        print(f"\nPolicy saved successfully to: {output_path}")


if __name__ == "__main__":
    main()
