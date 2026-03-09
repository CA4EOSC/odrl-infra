# ODRL Infrastructure for AI Agents

This guide explains how AI agents can interact with the ODRL infrastructure to manage identity, access restricted resources, and use time-limited credentials.

## 1. Restricted DIDs (Encrypted Resources)

Restricted DIDs allow you to share sensitive data that only a specific recipient (identified by their DID) can read.

### Workflow: Creating a Restricted Resource
1.  **Identify Recipient**: Get the recipient's DID (e.g., `did:oyd:zQmWvLG...`).
2.  **Create Restricted DID**: Call `POST /api/did/create/restricted`.
    ```bash
    curl -X 'POST' 'https://odrl.dev.codata.org/api/did/create/restricted' \
    -d '{"payload": {"secret": "data"}, "target_did": "did:oyd:zQmRecipient..."}'
    ```
3.  **Secure the Keys**: The response includes the `private_key`. **This must be shared securely with the recipient** (e.g., via a secure channel).

### Workflow: Resolving a Restricted Resource
1.  **Receive DID and Key**: The agent receives a Restricted DID and the corresponding private key.
2.  **Decrypt**: Call `POST /api/did/resolve/restricted`.
    ```bash
    curl -X 'POST' 'https://odrl.dev.codata.org/api/did/resolve/restricted' \
    -d '{"did": "did:oyd:zQmRestricted...", "private_key": "z1S5..."}'
    ```
3.  **Error Handling**: If decryption fails with `Decryption failed. Ciphertext failed verification`, it means the provided `private_key` does not match the one used to encrypt the DID for that specific recipient.

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

## 3. Best Practices for Agents
-   **Immutability**: Once a DID is created, its history is immutable. Use `update` for state changes.
-   **Key Management**: Never leak the `private_key` of a Restricted DID.
-   **TTL Strategy**: Use short-lived VCs (1-4 hours) for high-risk operations and longer-lived ones (24 hours) for routine tasks.
