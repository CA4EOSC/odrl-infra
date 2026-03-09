---
description: how to issue and verify time-limited credentials
---

### Verifiable Credentials with TTL (Time-To-Live)

You can issue credentials that have a built-in expiration date. This is useful for providing temporary access (e.g., 1 hour or 24 hours) to resources or for AI agent authorization.

#### 1. Issue a Credential with TTL

To issue a credential with a 24-hour lifespan, use the `/api/vc/issue` endpoint and specify the `ttl_hours` parameter.

```bash
curl -X 'POST' \
  'https://odrl.dev.codata.org/api/vc/issue' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "subject_did": "did:oyd:zQmSubjectDID...",
  "claims": {
    "role": "temporary-analyst",
    "access": "restricted-dataset-alpha"
  },
  "ttl_hours": 24
}'
```

The response will contain a `vc` object with an `expirationDate` field:

```json
{
  "vc": {
    "@context": [...],
    "type": "VerifiableCredential",
    "credentialSubject": {
      "id": "did:oyd:zQmSubjectDID...",
      "role": "temporary-analyst",
      "access": "restricted-dataset-alpha"
    },
    "expirationDate": "2026-03-08T21:30:32Z",
    "issuer": "did:oyd:zQmIssuerDID...",
    "proof": { ... }
  }
}
```

#### 2. Verify a Credential

To verify a credential (checking both the cryptographic signature and the expiration date), use the `/api/vc/verify` endpoint.

```bash
curl -X 'POST' \
  'https://odrl.dev.codata.org/api/vc/verify' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "vc": { ... issued vc object ... }
}'
```

#### 3. Expected Verification Results

*   **Valid & Not Expired**: Returns `{"valid": true, "verification": { ... }}`
*   **Expired**: Returns `{"valid": false, "error": "Credential has expired", "expirationDate": "..."}`
*   **Tampered/Invalid Signature**: Returns `{"valid": false, "error": "Signature verification failed"}`

#### 4. Supported Generic Types

You can specify a custom `type` for your credential:

```json
{
  "subject_did": "did:oyd:...",
  "claims": { ... },
  "type": "AccessCredential",
  "ttl_hours": 1
}
```
