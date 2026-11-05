# OYDID Skills

This document outlines the capabilities available in the OYDID system.

## ODRL API Skill

The ODRL API service provides a RESTful interface for managing DIDs and issuing Verifiable Credentials.

### API Endpoints

- **Create DID**: `POST /did/create`
  - Body: `{"payload": {"key": "value"}}`
- **Read DID**: `GET /did/{did}`
- **Update DID**: `POST /did/update`
  - Body: `{"did": "did:oyd:...", "payload": {"key": "new_value"}}`
- **Revoke DID**: `DELETE /did/{did}`
- **Create Restricted DID**: `POST /did/create/restricted`
  - Body: `{"payload": {...}, "target_did": "did:oyd:targetUserKey"}`
  - Encrypts the payload for the recipient identified by `target_did`.
- **Resolve Restricted DID**: `POST /did/resolve/restricted`
  - Body: `{"did": "did:oyd:...", "private_key": "z1S5..."}`
  - Decrypts the restricted DID using the recipient's private key.


### Bookmark DIDs

- **Create from URL**: `GET /did/create_from_url?url={url}&token={did}`
  - Fetches the URL, extracts title, and creates a DID with payload `{ "url": "...", "title": "...", "timestamp": "...", "token": "..." }`.
  - Supports **RDF Turtle** parsing: extracts titles and properties by language.
  - `did` (string): The DID to resolve. Can include a language tag suffix (e.g., `did:oyd:123...@fr`) to filter RDF properties.
- `language` (string, optional): Language code for filtering RDF properties (e.g., "en", "fr"). Overrides the tag in the DID if both are present.
- `token` (string, optional): DID token for access control, if required.
  - Returns the DID and the stored payload.
- **Share/Resolve DID**: `GET /did/share/{did}?language={lang}&token={did}`
  - Resolves the DID and returns the bookmark payload.
  - If the source was RDF, returns the title and properties in the requested `language`.
  - Accepts optional `token` parameter.

### Verifiable Credentials

- **Issue Google VC**: `POST /vc/google`
  - Body: `{"token": "GOOGLE_ID_TOKEN", "subject_did": "did:oyd:..."}`
- **Issue SSH Key VC**: `POST /vc/ssh`
  - Body: `{"public_key": "ssh-ed25519 ...", "signature": "SIG_CONTENT", "subject_did": "did:oyd:...", "username": "oydid-user"}`
  - Note: Signature must be generated via `ssh-keygen -Y sign -f key -n oydid data_file` where `data_file` contains the `subject_did`.
- **Issue GitHub VC**: `POST /vc/github`
  - Body: `{"token": "GITHUB_ACCESS_TOKEN", "subject_did": "did:oyd:..."}`
- **Issue ORCID VC**: `POST /vc/orcid`
  - Body: `{"token": "ORCID_ACCESS_TOKEN", "orcid": "ORCID_ID", "subject_did": "did:oyd:..."}`

### ODRL Access Control Profile (OAC)

- **Create OAC Policy**: `POST /oac/policy`
  - Body: JSON-LD OAC Policy (Preference, Requirement, Offer, Request, Agreement)
  - Example:
    ```json
    {
      "@context": "https://w3id.org/oac/context.json",
      "type": "Preference",
      "odrl:uid": "ex:preference1",
      "odrl:permission": [...]
    }
    ```
- **Get OAC Policy**: `GET /oac/policy/{uid}`

## ODRL CLI Skill

The OYDID CLI allows for direct interaction with the DID network.

### Basic Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `create` | Create a new DID | `echo '{"hello":"world"}' \| oydid create` |
| `read` | Resolve a DID Document | `oydid read did:oyd:...` |
| `update` | Update a DID Document | `echo '{"hello":"new"}' \| oydid update did:oyd:...` |
| `revoke` | Revoke a DID | `oydid revoke did:oyd:...` |
| `encrypt` | Encrypt payload for a DID | `echo '{"secret":"data"}' \| oydid encrypt did:oyd:target` |
| `decrypt` | Decrypt with a private key | `echo 'JWE_DATA' \| oydid decrypt --doc-enc z1S5...` |

### Verifiable Credentials

To issue a VC:
```bash
oydid vc-issue --issuer did:oyd:issuer... --subject did:oyd:subject...
```

## Testing Suite

All automated tests are located in the `tests/` directory:
- `tests/test_bookmark_did.py`: Bookmark DID creation and RDF resolution.
- `tests/test_cdif_vocab.py`: CDIF SKOS vocabularies, action mappings, and policy validation.
- `tests/test_did_api.py`: Core DID API endpoints lifecycle.
- `tests/test_existing_policies.py`: Policy listing, full-text searching, and indexing.
- `tests/test_google_check.py`: Google Verifiable Credential issuing.
- `tests/test_oac.py`, `tests/test_oac_example.py`: ODRL Access Control Profile (OAC) policies.
- `tests/test_oauth_vc.py`: GitHub and ORCID OAuth VC issuing.
- `tests/test_oydid.py`: Local CLI lifecycle testing (skips when CLI is not installed on host).
- `tests/test_policy_metadata.py`: Policy metadata date stamping and versioning.
- `tests/test_rdf_did.py`: RDF Turtle DID creation and multilingual queries.
- `tests/test_ssh_vc.py`: SSH VC issuing and signature verification.
- `tests/test_theme.py`: UI branding/theme configuration endpoints.

### Running All Tests

Execute the automated test runner script from the repository root:
```bash
./test_all.script
# or
./test_all.sh
```

This runs:
1. Python unit, integration, and vocabulary tests with `pytest tests/ -v`.
2. Frontend production build with `npm run build` in `frontend/`.

