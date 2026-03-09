# ODRL Infrastructure (DID-based)

This repository implements a **DID-based Open Digital Resource Language (ODRL)** infrastructure. It leverages **Decentralized Identifiers (DIDs)** and **Verifiable Credentials (VCs)** to create, sign, and verify digital policies and access rights.

Built with **FastAPI** and **Docker**, utilizing [OYDID](https://github.com/OwnYourData/oydid) for the underlying DID operations.

For more information on using the system as an AI agent, see [AGENTS.md](./AGENTS.md).

## Features

### 1. ODRL Access Control
Implements the ODRL Information Model using DIDs for identity and VCs for attributes.
-   **Universal Identity**: Assigners, Assignees, and Assets are identified by DIDs.
-   **Policy Management**: Create and store ODRL policies (Offers, Agreements, Privacy Policies, Requests).
-   **Verification**: Cryptographically verify that a requestor meets the requirements of a policy using Verifiable Credentials.

### 2. Restricted DIDs (Encrypted Resources)
Create and share resources that are cryptographically restricted to a specific recipient.
-   **Targeted Encryption**: Resources are encrypted using the public key of a **Target DID**.
-   **Recipient Decryption**: Only the holder of the **Target DID's Private Key** can decrypt and view the payload.
-   **Resolution**: Restricted DIDs resolve to a W3C Document containing `encrypted_data` (JWE format).

### 3. Verifiable Credentials (VCs)
Issue and verify credentials to prove identity and attributes for ODRL policies.
-   **Google Account**: Prove ownership of a Google email.
-   **GitHub Account**: Prove ownership of a GitHub handle.
-   **SSH Keys**: Link an SSH public key to a DID.
-   **ORCID**: Link an ORCID iD to a DID.
-   **Generic/Temporary**: Issue custom VCs with a **TTL (Time-To-Live)** for 1-24 hour restricted access.

### 3. DID Management
Full lifecycle management for OYDID (Listen-to-Yourself) DIDs.
-   **CRUD**: Create, Read, Update, Revoke DIDs.
-   **Bookmarks**: Create DIDs from URLs (with RDF Turtle support for Semantic Web resources).
-   **Resolution**: Resolve DIDs to retrieve documents and metadata.

### 4. React Frontend
A modern web interface to interact with the API:
-   **Dashboard**: Overview of services.
-   **DID Manager**: UI to resolve, create, and bookmark DIDs.
-   **VC Wallet**: Issue credentials (Google, GitHub, SSH, ORCID).
-   **Policy Builder**: Visual tool to create and validate ODRL policies.
-   **Prompts Manager**: Anchor LLM prompts as immutable DIDs.

## API Documentation

The API provides the following endpoints. You can also view interactive documentation at `/api/docs` when running the service.

### 1. ODRL Access Control (`/oac`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/oac/policy` | **Create ODRL Policy**. Accepts ODRL policies (Offer, Agreement, Request) in JSON-LD format. |
| `GET` | `/oac/policy/{uid}` | **Get ODRL Policy**. Retrieves a previously stored policy by its `odrl:uid`. |

### 2. Verifiable Credentials (`/vc`)

Issue W3C Verifiable Credentials to prove identity or properties.

| Method | Endpoint | Description | Payload |
| :--- | :--- | :--- | :--- |
| `POST` | `/vc/google` | **Google Account VC**. Proves ownership of a Google email. | `{"token": "id_token", "subject_did": "did:oyd:..."}` |
| `POST` | `/vc/github` | **GitHub Account VC**. Proves ownership of a GitHub username. | `{"token": "access_token", "subject_did": "did:oyd:..."}` |
| `POST` | `/vc/orcid` | **ORCID VC**. Proves ownership of an ORCID iD. | `{"token": "access_token", "orcid": "...", "subject_did": "did:oyd:..."}` |
| `POST` | `/vc/ssh` | **SSH Key VC**. Links an SSH public key to a DID. | `{"username": "...", "public_key": "...", "signature": "...", "subject_did": "..."}` |
| `POST` | `/vc/issue` | **Issue Generic VC**. Create custom credentials with an optional **TTL**. | `{"subject_did": "...", "claims": {...}, "ttl_hours": 24}` |
| `POST` | `/vc/verify` | **Verify VC**. Cryptographically validates a VC and checks for **expirationDate**. | `{"vc": { ... }}` |

### 3. DID Operations (`/did`)

Manage the lifecycle of OYDID Data Resources.

| Method | Endpoint | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `POST` | `/did/create` | **Create DID**. Creates a new DID with a given JSON payload. | Body: `{"payload": {...}, "options": {...}}` |
| `POST` | `/did/create/restricted` | **Create Restricted DID**. Encrypts payload for a target DID using `oydid encrypt`. | Body: `{"payload": {...}, "target_did": "did:oyd..."}` |
| `GET` | `/did/create_from_url` | **Bookmark DID**. Creates a DID from a URL, extracting title and metadata. | `?url=...` (Supports `.ttl` for RDF) |
| `GET` | `/did/share/{did}` | **Resolve/Share**. Resolves a DID and returns its payload (e.g., bookmark data). | `?language=fr` (or `did:oyd:...@fr`) |
| `GET` | `/did/{did}` | **Read DID**. Resolves the full DID Document. | Path: `did` |
| `GET` | `/did/resolve/{did}` | **Resolve DID**. Resolves a DID to its full W3C DID Document. | Path: `did` |
| `POST` | `/did/resolve/restricted` | **Decrypt Restricted DID**. Resolves and decrypts a restricted DID using a private key. | Body: `{"did": "...", "private_key": "..."}` |
| `GET` | `/did/validate/{did}` | **Validate DID**. Validates a DID and optionally checks if a `public_key` is authorized for it. | `?public_key=...` |
| `POST` | `/did/update` | **Update DID**. Updates the payload of an existing DID. | Body: `{"did": "...", "payload": {...}}` |
| `DELETE` | `/did/revoke/{did}` | **Revoke DID**. Revokes a DID, making it invalid. | Path: `did` |

### 4. Utilities

-   `GET /health`: Service health check.

## Getting Started

### Prerequisites
-   Docker & Docker Compose
-   Git

### Running the Service
1.  **Clone the repository** (ensure submodules are initialized):
    ```bash
    git clone --recurse-submodules https://github.com/4tikhonov/odrl-infra.git
    cd odrl-infra
    ```
    *If you already cloned without submodules:*
    ```bash
    git submodule update --init --recursive
    ```

2.  **Run with Docker Compose**:
    ```bash
    docker compose up --build
    ```

    The service will start on `http://localhost:8001`:
    -   **Frontend**: [http://localhost:8001/](http://localhost:8001/)
    -   **API Docs**: [http://localhost:8001/api/docs](http://localhost:8001/api/docs)
    -   **Health Check**: [http://localhost:8001/api/health](http://localhost:8001/api/health)

    *Note: The frontend is built and served directly by the FastAPI container.*

## Architecture
-   **FastAPI**: Provides the REST API layer.
-   **OYDID**: Submodule handling all core DID and VC operations.
-   **Docker**: Encapsulates the runtime environment (Python + Ruby for OYDID CLI).
