# ODRL Infrastructure for AI Agents

This guide explains how AI agents can interact with the ODRL infrastructure to manage identity, access restricted resources, and use time-limited credentials.

## 1. Restricted DIDs (Encrypted Resources)

Restricted DIDs allow you to share sensitive data that only a specific recipient (identified by their DID) can read.

### Workflow: Creating a Restricted Resource
1.  **Identify Recipient**: Get the recipient's DID (e.g., `did:oyd:zQmWvLG...`).
2.  **Create Restricted DID**: Post the payload to `/api/did/create/restricted`.
    ```bash
    curl -X 'POST' 'https://odrl.dev.codata.org/api/did/create/restricted' \
    -d '{"payload": {"secret": "data"}, "target_did": "did:oyd:zQmRecipient..."}'
    ```
    Or via JSON body:
    ```json
    POST /api/did/create/restricted
    {
      "payload": { "secret_key": "ABC-123", "instructions": "Move to sector 7" },
      "target_did": "did:oyd:RecipientDID"
    }
    ```
3.  **Secure the Keys**: The response includes the `private_key`. **This must be shared securely with the recipient** (e.g., via a secure channel).

### Workflow: Resolving a Restricted Resource
1.  **Receive DID and Key**: The agent receives a Restricted DID and the corresponding private key (the `z1S5...` multibase string).
2.  **Decrypt**: Post the DID and your private key to `/api/did/resolve/restricted`.
    ```bash
    curl -X 'POST' 'https://odrl.dev.codata.org/api/did/resolve/restricted' \
    -d '{"did": "did:oyd:zQmRestricted...", "private_key": "z1S5..."}'
    ```
3.  **Error Handling**: 
    - **400 Bad Request: "Ciphertext failed verification"**: This typically means the private key provided belongs to a different DID than the one specified as the `target_did` during encryption.
    - **400 Bad Request: "Missing encrypted_data"**: The DID you are trying to resolve is not a restricted/encrypted DID. Use the standard `/api/did/{did}` for non-secret documents.

---

## 2. Time-Limited Access (Verifiable Credentials with TTL)

For temporary authorization (e.g., granting an agent access for 1 to 24 hours), use Verifiable Credentials with a Time-To-Live (TTL).

### Workflow: Issuing Temporary Credentials
The issuer (e.g., a data owner) grants temporary rights to an agent's DID.

1.  **Issue VC**: Call `POST /api/vc/issue`.
    ```bash
    curl -X 'POST' 'https://odrl.dev.codata.org/api/vc/issue' \
    -d '{
      "subject_did": "did:oyd:zQmAgent...",
      "claims": {"access": "granted", "scope": "read-only"},
      "ttl_hours": 24
    }'
    ```
2.  **Expiration date**: The system embeds an `expirationDate` in the VC based on the `ttl_hours`.

### Workflow: Verifying Access
Before performing an action, a service verifies the agent's credential.

1.  **Verify VC**: Call `POST /api/vc/verify`.
    ```bash
    curl -X 'POST' 'https://odrl.dev.codata.org/api/vc/verify' \
    -H 'Content-Type: application/json' \
    -d '{"vc": { ... actual vc object ... }}'
    ```
2.  **Result Interpretation**:
    *   **Valid**: `{"valid": true, ...}` - Access granted.
    *   **Expired**: `{"valid": false, "error": "Credential has expired"}` - Access denied.

---

## 3. Identifying and Managing Keys

When creating a DID through `/api/did/create`, the response includes:
- `did`: The public identifier.
- `keys`:
    - `private_key`: Used for data decryption (if this is a target DID).
    - `revocation_key`: Used to revoke the DID.
    - `revocation_log`: The raw revocation record.

**CRITICAL**: As an agent, store the `private_key` securely. It is the only way to decrypt resources shared with you.

## 4. Best Practices for Agents
-   **Immutability**: Once a DID is created, its history is immutable. Use `update` for state changes.
-   **Key Management**: Never leak the `private_key` of a Restricted DID.
-   **TTL Strategy**: Use short-lived VCs (1-4 hours) for high-risk operations and longer-lived ones (24 hours) for routine tasks.

## References

-   Vyacheslav Tykhonov, Anton Polishko, Artur Kiulian, and Maksym Komar. (2020). **CoronaWhy: Building a Distributed, Credible and Scalable Research and Data Infrastructure for Open Science**. SciNLP workshop at AKBC 2020. [https://doi.org/10.5281/zenodo.3922256](https://doi.org/10.5281/zenodo.3922256)
-   Vyacheslav Tykhonov. (2023, July 11). **Decentralized research data infrastructure and knowledge graphs**. Zenodo. [https://doi.org/10.5281/zenodo.8134041](https://doi.org/10.5281/zenodo.8134041)
-   Tykhonov, V. (2023). **Sustaining Controlled Vocabularies and Ontologies with Decentralization and DIDs**. In Convention Loi & Commun. edited by: Danièle Bourcier, Paul Bourgine, and Salma Mesmoudi. Association Française de Science des Systèmes (AFSCET), 2024. Zenodo. [https://doi.org/10.5281/zenodo.10375766](https://doi.org/10.5281/zenodo.10375766)
-   Andrey Vukolov, Erik van Winkle, Vyacheslav Tykhonov, Roberto Pugliese. (2024). **Decentralised Persistent Identification - an Emerging Technology for Sustainability Maintenance and Knowledge-driven Processes**. IFAC-PapersOnLine, Volume 58, Issue 8, Pages 371-376. [https://doi.org/10.1016/j.ifacol.2024.08.149](https://doi.org/10.1016/j.ifacol.2024.08.149)
-   Tykhonov, V. (2024, November 29). **Pros and Cons of Decentralized Identifiers (DIDs) in Dataverse**. "Dataverse and AI" workshop, FORS, Lausanne, Switzerland. Zenodo. [https://doi.org/10.5281/zenodo.14623002](https://doi.org/10.5281/zenodo.14623002)
-   Tykhonov, V. (2025, June 23). **Decentralized identifiers (DIDs) for sustainable AI in the Dataverse data network**. Semantic Croissant regular meeting. Zenodo. [https://doi.org/10.5281/zenodo.15723145](https://doi.org/10.5281/zenodo.15723145)
