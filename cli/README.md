# ODRL & OAC Policy Generation & Validation Engine

This CLI toolkit and backend architecture implement a step-by-step policy creation workflow based on:
1. **W3C ODRL 2.2 Recommendation**: [W3C ODRL Vocabulary & Action Concepts](https://www.w3.org/TR/odrl-vocab/#actionConcepts)
2. **OAC (ODRL Access Control / Privacy Profile)**: [ODRL Access Control (OAC)](https://w3id.org/oac/) & [Data Privacy Vocabulary (DPV)](https://w3id.org/dpv#)
3. **DUODRL Profile**: [GA4GH Data Use Ontology to ODRL mappings](https://w3id.org/duodrl#)
4. **W3C SHACL Validation**: [Shapes Constraint Language (SHACL)](https://www.w3.org/TR/shacl/)

---

## 1. Overview of the Policy Process

The policy creation and enforcement process follows a strict 5-stage pipeline:

```
[1. Policy Modeling & Type Selection]
             │
             ▼
[2. Target Asset & Rule Definition (Permission / Prohibition / Duty)]
             │
             ▼
[3. Action Concept & Constraint Specification (DPV / DUODRL)]
             │
             ▼
[4. Multi-Layer Validation (Structural + Pydantic + SHACL Shape)]
             │
             ▼
[5. Persistence, DID Anchoring & Decentralized Storage (OYDID & Qdrant)]
```

### Stage 1: Policy Modeling & Type Selection
Every policy defines a high-level contract type specified by `@type`:
- **`odrl:Offer`**: An offer made by the data owner/provider (`assigner`) setting conditions under which assets can be accessed (e.g. solid web user profile card offers).
- **`odrl:Agreement`**: A bilateral agreement binding both `assigner` and `assignee`.
- **`odrl:Set`**: General-purpose specification of rights without fixed parties (used for catalog licenses, DUO consent codes, CC licenses).
- **`odrl:Request`**: A consumer/client requesting specific data operations.

### Stage 2: Rule Formulation
Policies group rules into three foundational primitives:
- **`odrl:permission`**: Operations that the assignee is permitted to perform on the target asset. Can optionally carry a **`dpv:hasContext`** (`dpv:Required` vs `dpv:Optional`) for data protection regulations.
- **`odrl:prohibition`**: Operations strictly forbidden (e.g., commercial exploitation, redistribution prior to a moratorium date).
- **`odrl:obligation`**: Consequential actions or duties that must be satisfied (e.g., attribution, notification, ethics review).

### Stage 3: W3C Action Concepts, Refinements & Constraints
1. **Action Concept Selection**: Each rule binds a canonical action from the 54 W3C ODRL operations (`odrl:read`, `odrl:use`, `odrl:distribute`, `odrl:derive`, etc.) or privacy extensions (`oac:Read`).
2. **Action Refinements (`odrl:refinement`)**: Narrow or parameterize the operational execution of the action itself (e.g. spatial boundaries, delivery channel, output format).
3. **Rule Constraints (`odrl:constraint`)**: Formulate atomic triple conditions defining under what circumstances the rule is applicable (e.g., purpose matching, time windows, party identity).

### Stage 4: Multi-Layer Validation
Before any policy can be saved, exported, or anchored, it undergoes automated verification:
1. **Structural Checks**: Verifies presence of `@context`, `@type`, `odrl:uid`, and at least one rule with valid actions, targets, and refinement/constraint structures.
2. **Pydantic Model Schema**: Validates syntax against `app.models_oac.OacPolicy` and `OacAction`.
3. **W3C SHACL Validation**: Evaluates the RDF graph against [cli/shacl/odrl_shape.ttl](shacl/odrl_shape.ttl) ensuring node shape, cardinality, datatype, and action refinement path compliance.

### Stage 5: DID Anchoring & Indexing
- The policy payload is transformed into an immutable cryptographic DID Document using the **OYDID protocol** (`did:oyd:...`).
- The policy is indexed in **Qdrant Vector Database** for semantic search and fast retrieval.

---

## 2. In-Depth Anatomy: Actions, Refinements, and Constraints

Understanding the semantic boundary between an **Action**, an **Action Refinement**, and a **Rule Constraint** is critical in W3C ODRL 2.2 and OAC.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ODRL Rule (Permission / Prohibition)                                                   │
│                                                                                        │
│  ├── odrl:target ───► Target Asset (e.g. duodrl:TemplateDataset, oac:Identifier)       │
│  │                                                                                     │
│  ├── odrl:action ───► What is performed? (e.g. odrl:distribute, odrl:use)              │
│  │     │                                                                               │
│  │     └── odrl:refinement ───► Qualifies / narrows the action itself                  │
│  │           │                  (e.g., delivery channel, spatial area, resolution)     │
│  │           ├── odrl:leftOperand:  odrl:spatial                                       │
│  │           ├── odrl:operator:     odrl:eq                                            │
│  │           └── odrl:rightOperand: https://sws.geonames.org/2921044/ (Germany)        │
│  │                                                                                     │
│  └── odrl:constraint ───► World state condition required for the rule to apply         │
│        │                  (e.g., user purpose, current time, credential, role)         │
│        ├── odrl:leftOperand:  oac:Purpose                                              │
│        ├── odrl:operator:     odrl:isA                                                 │
│        └── odrl:rightOperand: dpv:IdentityVerification                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1. Actions (`odrl:action`)
An **Action** represents an operation on a target asset.
- **Definition**: It specifies the core operation permitted, prohibited, or required.
- **W3C Standard Taxonomy**: The W3C ODRL 2.2 vocabulary defines **54 action concepts** organized in an inheritance hierarchy (`odrl:includedIn`):
  - *Usage Actions*: `odrl:use` (root of all actions), `odrl:read`, `odrl:display`, `odrl:execute`, `odrl:play`.
  - *Transfer Actions*: `odrl:distribute`, `odrl:grantUse`, `odrl:transfer`.
  - *Transformation Actions*: `odrl:derive`, `odrl:modify`, `odrl:aggregate`, `odrl:anonymize`, `odrl:translate`.
  - *Asset Management*: `odrl:delete`, `odrl:archive`, `odrl:index`, `odrl:install`.
- **Privacy & DPV Extensions**: The OAC profile introduces semantic actions such as `oac:Read`, `oac:Write`, `oac:Process`.
- **Serialization Modes**:
  - **Unrefined (String IRI)**: When no refinements are needed:
    ```json
    "odrl:action": "oac:Read"
    ```
  - **Refined (Action Object)**: When qualified with refinements, uses `rdf:value` and `odrl:refinement`:
    ```json
    "odrl:action": {
      "rdf:value": { "@id": "odrl:distribute" },
      "odrl:refinement": [
        {
          "dcterms:title": "Geographic delivery restriction",
          "odrl:leftOperand": "odrl:spatial",
          "odrl:operator": "odrl:eq",
          "odrl:rightOperand": "https://sws.geonames.org/2921044/"
        }
      ]
    }
    ```

### 2.2. Action Refinements (`odrl:refinement`)
An **Action Refinement** applies constraints directly to the **Action**, narrowing its semantics without creating a brand-new vocabulary term.
- **Purpose**: It qualifies *how, where, or in what manner* an action is performed.
- **Typical Use Cases**:
  - **Spatial / Jurisdiction Scope**: Distribute or read, but restricted to a specific region (`odrl:spatial eq https://sws.geonames.org/2921044/`).
  - **Quality / Resolution**: Print or render, but limited to a max resolution (`resolution lteq 300 dpi`).
  - **Delivery Channel**: Distribute, but only via secure mobile or TLS channel (`deliveryChannel eq mobileNetwork`).
  - **Encoding / Media**: Export, but only into an approved format (`media eq application/pdf`).
- **Structure**: Each refinement is an instance of `odrl:Constraint` with:
  - `odrl:leftOperand`: The parameter of the action being constrained (e.g. `odrl:spatial`, `odrl:deliveryChannel`, `odrl:resolution`).
  - `odrl:operator`: The comparison operator (e.g. `odrl:eq`, `odrl:lteq`, `odrl:isPartOf`).
  - `odrl:rightOperand`: The limit, threshold, or concept identifier.
  - `dcterms:title`: (Optional) Human-readable explanation.

### 2.3. Rule Constraints (`odrl:constraint`)
A **Rule Constraint** applies to the overall **Permission**, **Prohibition**, or **Duty**.
- **Purpose**: It asserts a logical condition that must hold true for the rule to become active and enforceable.
- **Typical Use Cases**:
  - **Purpose Constraints (OAC / DPV / DUO)**: Access allowed only for non-commercial general research (`oac:Purpose odrl:isA duodrl:GRU`) or identity verification (`oac:Purpose odrl:isA dpv:IdentityVerification`).
  - **Temporal Constraints**: Prohibitions active until a publication moratorium expires (`odrl:dateTime odrl:lt 2026-12-31T23:59:59Z`).
  - **Execution Count Limits**: Permission valid for up to 5 accesses (`odrl:count odrl:lteq 5`).
  - **Party / Subject Eligibility**: Only assignees possessing a specific verifiable credential or role (`odrl:recipient odrl:eq did:oyd:...`).
- **Structure**:
  - `odrl:leftOperand`: The contextual aspect being evaluated (`oac:Purpose`, `odrl:dateTime`, `odrl:recipient`, `odrl:count`).
  - `odrl:operator`: `odrl:isA`, `oac:isNotA`, `odrl:eq`, `odrl:lt`, `odrl:lteq`, `odrl:gt`, `odrl:gteq`.
  - `odrl:rightOperand`: The expected value, timestamp, or ontology concept IRI.
  - `dcterms:title`: (Optional) Human-readable rationale.

### 2.4. Summary Comparison: Constraints vs. Refinements

| Dimension | Action Refinement (`odrl:refinement`) | Rule Constraint (`odrl:constraint`) |
| :--- | :--- | :--- |
| **Location** | Nested inside `odrl:action` | Directly on `odrl:permission`, `odrl:prohibition`, or `odrl:duty` |
| **Target of qualification** | The operational action (e.g. `distribute`, `read`) | The overall policy rule and legal permission/prohibition |
| **Question answered** | *How, where, or in what manner is the action executed?* | *Under what real-world conditions is this rule valid?* |
| **Typical Left Operands** | `odrl:spatial`, `odrl:deliveryChannel`, `odrl:resolution`, `odrl:media` | `oac:Purpose`, `odrl:dateTime`, `odrl:count`, `odrl:recipient`, `dpv:LegalBasis` |
| **Example** | `"Only distribute within EU countries"` | `"Only use if purpose is academic research"` |
| **JSON-LD Serialization** | `odrl:action: { "rdf:value": ..., "odrl:refinement": [...] }` | `odrl:constraint: [ { "odrl:leftOperand": ..., ... } ]` |

---

## 3. Directory Structure

```
cli/
├── create_policy.py      # Interactive CLI wizard, validator, and preset generator
├── README.md             # This guide
├── data/                 # Sample generated policies (JSON-LD)
│   ├── duo_0000042.json  # General Research Use (GRU) permission
│   ├── duo_0000024.json  # Publication Moratorium prohibition
│   └── listing_4_2.json  # Solid Web / OAC Offer with consent context
└── shacl/
    └── odrl_shape.ttl    # W3C SHACL shape definition for ODRL & OAC
```

---

## 4. CLI Usage Guide

### 4.1. Interactive Step-by-Step Wizard
Launch the guided CLI wizard:
```bash
python3 cli/create_policy.py
```
The wizard interactively guides you through:
1. Selecting Policy Type (`Offer`, `Agreement`, `Set`, `Request`)
2. Entering Policy UID (`urn:uuid:...` or `did:oyd:...`)
3. Specifying Metadata (`dcterms:description`, `dcterms:creator`, `dcterms:source`)
4. Adding Permissions with DPV Consent Context, Action Refinements, and Purpose Constraints
5. Adding Prohibitions with Output Asset bindings, Action Refinements, and Date/Entity Constraints
6. Running the internal `Validator`
7. Exporting to a JSON-LD file

### 4.2. List All W3C Action Concepts
Print the full taxonomy of 54 W3C actions with their descriptions and `includedIn` hierarchy:
```bash
python3 cli/create_policy.py --list-actions
```

### 4.3. Quick Presets
Generate pre-configured standard templates directly:

```bash
# GA4GH DUO 0000042: General Research Use
python3 cli/create_policy.py --quick-preset duo-0000042 -o cli/data/duo_0000042.json

# GA4GH DUO 0000024: Publication Moratorium
python3 cli/create_policy.py --quick-preset duo-0000024 -o cli/data/duo_0000024.json

# Solid Web Listing 4.2: OAC Offer with Identity Verification & Age restrictions
python3 cli/create_policy.py --quick-preset listing-4.2 -o cli/data/listing_4_2.json

# CC-BY Equivalent Open Access with Attribution Duty
python3 cli/create_policy.py --quick-preset cc-by-attribution -o my_policy.json
```

---

## 5. FastAPI Policy Service Integration

The logic in `create_policy.py` is served as a RESTful microservice under `/api/policy`:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/policy/vocab/actions` | `GET` | Catalog of 54 canonical W3C actions grouped by category |
| `/api/policy/vocab/helpers` | `GET` | Pre-indexed operands, operators, and DUODRL mappings |
| `/api/policy/presets/{name}`| `GET` | Fetches JSON-LD preset (`duo-0000042`, `listing-4.2`, etc.) |
| `/api/policy/validate`      | `POST`| Validates any JSON-LD policy against SHACL and Pydantic rules |
| `/api/policy/create`        | `POST`| Validates and anchors the policy into an OYDID Decentralized Identifier |

---

## 6. SHACL Shape Verification

The SHACL shapes in [cli/shacl/odrl_shape.ttl](shacl/odrl_shape.ttl) enforce the following rules:
- **`ex:PolicyShape`**: Ensures valid identifier (`odrl:uid`), optional metadata (`dcterms:creator`, `dcterms:description`), and at least one rule.
- **`ex:PermissionShape`**: Mandates `odrl:target` and `odrl:action`, validates `(odrl:action odrl:refinement)` against `ConstraintShape`, and validates optional `dpv:hasContext`.
- **`ex:ProhibitionShape`**: Mandates `odrl:target` and `odrl:action`, validates `(odrl:action odrl:refinement)` against `ConstraintShape`, and validates optional `odrl:output`.
- **`ex:ConstraintShape`**: Enforces complete triple constraint logic (`odrl:leftOperand`, `odrl:operator`, `odrl:rightOperand`).

Run manual RDF/SHACL validation via python:
```python
import pyshacl, rdflib, json

data_graph = rdflib.Graph().parse("cli/data/listing_4_2.json", format="json-ld")
shape_graph = rdflib.Graph().parse("cli/shacl/odrl_shape.ttl", format="turtle")

conforms, results_graph, results_text = pyshacl.validate(data_graph, shacl_graph=shape_graph)
print("Conforms:", conforms)
```

