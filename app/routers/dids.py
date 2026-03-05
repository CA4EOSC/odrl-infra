from fastapi import APIRouter, HTTPException, Query
from ..models import DidCreateRequest, DidCreateRestrictedRequest, DidResolveRestrictedRequest, DidUpdateRequest
from ..services.oydid import run_oydid_command
from ..services.qdrant_service import qdrant_service
import json
import requests
import os
import re
from datetime import datetime
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import DCTERMS, RDFS, FOAF, RDF, OWL, SKOS

SCHEMA = Namespace("http://schema.org/")

router = APIRouter(prefix="/did", tags=["DIDs"])

def parse_rdf_metadata(content, content_type="text/turtle", target_url=None):
    g = Graph()
    try:
        g.parse(data=content, format=content_type)
    except Exception as e:
        print(f"Error parsing RDF: {e}")
        return None

    metadata = {"titles": {}, "descriptions": {}, "properties": {}}
    
    # Identify Focus Node (for main title hint only)
    focus_node = None
    if target_url:
        target_uri = URIRef(target_url)
        if (target_uri, None, None) in g:
            focus_node = target_uri
    if not focus_node:
        for s in g.subjects(RDF.type, OWL.Ontology):
            focus_node = s
            break
    if not focus_node:
        for s in g.subjects(RDF.type, SKOS.ConceptScheme):
            focus_node = s
            break

    # Extract ALL properties for metadata from the entire graph
    title_preds = [DCTERMS.title, RDFS.label, SKOS.prefLabel, SCHEMA.name, FOAF.name]
    desc_preds = [DCTERMS.description, RDFS.comment, SCHEMA.description]
    
    # helper to track main title candidates
    # helper to track main title candidates
    main_titles = []
    
    concepts = {}
    
    for s, p, o in g:
        if isinstance(o, Literal):
            lang = o.language or "default"
            value = str(o)
            s_str = str(s)
            
            p_str = str(p)
            key = p_str.split("#")[-1].split("/")[-1] # simple local name
            
            if s_str not in concepts:
                concepts[s_str] = {"uri": s_str, "titles": {}, "descriptions": {}, "properties": {}}

            if p in title_preds:
                if lang not in concepts[s_str]["titles"]:
                    concepts[s_str]["titles"][lang] = []
                concepts[s_str]["titles"][lang].append(value)
                
                # Check for focus node hint
                if focus_node and s == focus_node and lang in ["en", "default"]:
                    main_titles.insert(0, value)
                elif not focus_node and lang in ["en", "default"]:
                     main_titles.append(value)

            elif p in desc_preds:
                if lang not in concepts[s_str]["descriptions"]:
                    concepts[s_str]["descriptions"][lang] = []
                concepts[s_str]["descriptions"][lang].append(value)
            
            else:
                 # Generic properties
                 if lang not in concepts[s_str]["properties"]:
                    concepts[s_str]["properties"][lang] = {}
                 if key not in concepts[s_str]["properties"][lang]:
                    concepts[s_str]["properties"][lang][key] = []
                 concepts[s_str]["properties"][lang][key].append(value)

    metadata["concepts"] = list(concepts.values())
    if main_titles:
        metadata["_main_title_hint"] = main_titles[0]

    return metadata

@router.get("/create_from_url")
async def create_did_from_url(url: str, token: str = Query(None, description="Optional DID token")):
    """
    Create a DID with payload derived from a URL.
    Extracts title and timestamp. Supports RDF Turtle.
    """
    if token and not token.startswith("did:"):
        raise HTTPException(status_code=400, detail="Token must be a valid DID starting with 'did:'")

    try:
        # 1. Fetch URL
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 2. Check Content Type / Extension
        content_type = response.headers.get("Content-Type", "").lower()
        is_turtle = "text/turtle" in content_type or url.endswith(".ttl")
        
        timestamp = datetime.now().isoformat()
        payload = {
            "url": url,
            "timestamp": timestamp
        }
        
        if is_turtle:
            rdf_meta = parse_rdf_metadata(response.text, content_type="turtle", target_url=url)
            if rdf_meta:
                 payload["rdf"] = rdf_meta
                 titles = rdf_meta.get("titles", {})
                 # Pick a default title
                 default_title = rdf_meta.get("_main_title_hint", "RDF Resource")
                 
                 if default_title == "RDF Resource":
                     # Try english then default then any
                     for lang in ["en", "default"]:
                         if lang in titles and titles[lang]:
                             default_title = titles[lang][0]
                             break
                     if default_title == "RDF Resource" and titles:
                         first_lang = list(titles.keys())[0]
                         if titles[first_lang]:
                             default_title = titles[first_lang][0]

                 payload["title"] = default_title
                 payload["is_rdf"] = True
            else:
                 payload["title"] = url
                 payload["is_rdf"] = False
        else:
            title_match = re.search(r'<title.*?>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else url
            payload["title"] = title
            payload["is_rdf"] = False
            
        if token:
            payload["token"] = token
        
        # 5. Create DID
        result = run_oydid_command(["create", "--json-output"], input_data=payload)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"OYDID creation failed: {result.stderr}")
            
        did_data = json.loads(result.stdout)
        did = did_data.get("did")
        
        # Store in Qdrant
        try:
            qdrant_service.upsert_document(did, payload)
        except Exception as e:
            print(f"Warning: Failed to store in Qdrant: {e}")
        
        return {
            "did": did,
            "doc": did_data.get("doc"),
            "stored_payload": payload
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.get("/fetch_jsonld")
async def fetch_jsonld(url: str):
    """
    Fetch JSON-LD from a URL (Backend proxy to avoid CORS).
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing JSON: {str(e)}")

@router.get("/share/{did}")
async def share_did(did: str, language: str = Query(None), token: str = Query(None)):
    """
    Resolve a DID and return its bookmark payload.
    Supports filtering by language for RDF payloads.
    Also supports DID format with language tag: did:oyd:...@fr
    """
    # Check for language tag in DID string
    if "&" in did:
        did = did.split("&")[0]
        
    if "@" in did:
        parts = did.split("@")
        did = parts[0]
        if not language and len(parts) > 1:
            language = parts[1]

    result = run_oydid_command(["read", did, "--json-output"])
    
    if result.returncode != 0:
        raise HTTPException(status_code=404, detail=f"DID not found or error: {result.stderr}")
        
    try:
        did_doc = json.loads(result.stdout)
        doc = did_doc.get("doc", {})
        log = did_doc.get("log", [])
        
        target_payload = doc
        if not target_payload.get("url") and isinstance(log, list):
             for entry in log:
                 if isinstance(entry, dict) and (entry.get("op") == 0 or entry.get("op") == "create"):
                      op_doc = entry.get("doc", {})
                      if op_doc.get("url"):
                          target_payload = op_doc
                          break
        
        if not target_payload:
            return {}

        payload = {
            "url": target_payload.get("url"),
            "timestamp": target_payload.get("timestamp"),
            "title": target_payload.get("title"),
            "token": target_payload.get("token")
        }
        
        if language and target_payload.get("is_rdf") and "rdf" in target_payload:
            rdf_data = target_payload["rdf"]
            concepts = rdf_data.get("concepts", [])
            
            # 1. Main Title
            # Try to find the title of the focus node (if hint exists) or just the first concept with that language?
            # Creating a "pairs" output for properties
            pairs = []
            
            for c in concepts:
                titles = c.get("titles", {})
                en_title = titles.get("en", titles.get("default", []))
                target_title = titles.get(language, [])
                
                if en_title and target_title:
                    # Create pair
                    pairs.append({
                        "en": en_title[0],
                        language: target_title[0]
                    })
            
            # Sort pairs by english title for consistency?
            pairs.sort(key=lambda x: x["en"])
            
            payload["concepts"] = pairs
            # Keep top-level title as well for the bookmark itself
            # Try to grab the main hint from metadata if preserved, or just keep what was in payload["title"]
            # existing logic preserved payload["title"] from create step which used the hint.
            
        elif not language and target_payload.get("is_rdf"):
             payload["rdf_metadata"] = target_payload.get("rdf")

        return payload
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}

def get_did_w3c_and_keys(did: str, did_data: dict) -> dict:
    """Helper to fetch W3C document and read associated local keys"""
    response_data = dict(did_data)
    
    # 1. Fetch W3C Document
    w3c_result = run_oydid_command(["read", did, "--w3c-did"])
    if w3c_result.returncode == 0:
        try:
            response_data["did_document"] = json.loads(w3c_result.stdout)
        except:
            pass
            
    # 2. Extract generated keys from local filesystem
    did10 = did.replace("did:oyd:", "").split("&")[0][:10]
    keys = {}
    
    priv_file = f"{did10}_private_key.enc"
    if os.path.exists(priv_file):
        with open(priv_file, "r") as f:
            keys["private_key"] = f.read().strip()
            
    rev_key_file = f"{did10}_revocation_key.enc"
    if os.path.exists(rev_key_file):
        with open(rev_key_file, "r") as f:
            keys["revocation_key"] = f.read().strip()
            
    rev_json_file = f"{did10}_revocation.json"
    if os.path.exists(rev_json_file):
        try:
            with open(rev_json_file, "r") as f:
                keys["revocation_json"] = json.loads(f.read())
        except:
            pass
            
    if keys:
        response_data["keys"] = keys
        
    return response_data

@router.post("/create")
async def create_did(request: DidCreateRequest):
    """Create a new DID"""
    result = run_oydid_command(["create", "--json-output"], input_data=request.payload)
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=400, detail=f"OYDID Error: {error_detail}")
        
    try:
        # If collection is explicitly provided, store it in the payload itself
        if request.collection:
            request.payload["collection"] = request.collection

        did_data = json.loads(result.stdout)
        did = did_data.get("did")
        
        # Store in Qdrant
        try:
            qdrant_service.upsert_document(did, request.payload, collection=request.collection)
        except Exception as e:
            print(f"Warning: Failed to store in Qdrant: {e}")
            
        return get_did_w3c_and_keys(did, did_data)
        
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}

@router.post("/create/restricted")
async def create_restricted_did(request: DidCreateRestrictedRequest):
    """Create a new restricted DID encrypted for a specific target DID"""
    # 1. Encrypt the payload using the target DID
    payload_json = json.dumps(request.payload)
    encrypt_result = run_oydid_command(["encrypt", "--from", request.target_did, "--json-output"], input_data=request.payload)
    
    if encrypt_result.returncode != 0:
        error_detail = getattr(encrypt_result, "error_msg", encrypt_result.stderr)
        raise HTTPException(status_code=400, detail=f"Encryption failed for target DID {request.target_did}: {error_detail}")
        
    try:
        encrypted_payload = json.loads(encrypt_result.stdout)
    except json.JSONDecodeError:
        # If output is not json but a JWE string or something
        encrypted_payload = {"jwe": encrypt_result.stdout.strip()}
        
    # include the restriction metadata
    final_payload = {
        "encrypted_data": encrypted_payload,
        "restricted_to": request.target_did
    }

    # 2. Create the DID with encrypted payload
    result = run_oydid_command(["create", "--json-output"], input_data=final_payload)
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=400, detail=f"OYDID Create Error: {error_detail}")
        
    try:
        if request.collection:
            final_payload["collection"] = request.collection

        did_data = json.loads(result.stdout)
        did = did_data.get("did")
        
        try:
            qdrant_service.upsert_document(did, final_payload, collection=request.collection)
        except Exception as e:
            print(f"Warning: Failed to store in Qdrant: {e}")
            
        return get_did_w3c_and_keys(did, did_data)
        
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}

@router.post("/resolve/restricted")
async def resolve_restricted_did(request: DidResolveRestrictedRequest):
    """Resolve and decrypt a restricted DID using the provided private key."""
    # 1. Resolve the DID to get the encrypted content
    did = request.did
    if "&" in did:
        did = did.split("&")[0]

    result = run_oydid_command(["read", did, "--json-output"])
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=404, detail=f"DID not found or error: {error_detail}")

    try:
        did_data = json.loads(result.stdout)
        doc = did_data.get("doc", {})
        encrypted_data = doc.get("encrypted_data")
        
        if not encrypted_data:
            # Fallback check in log
            log = did_data.get("log", [])
            for entry in log:
                if isinstance(entry, dict) and (entry.get("op") == 0 or entry.get("op") == "create"):
                     encrypted_data = entry.get("doc", {}).get("encrypted_data")
                     break
        
        if not encrypted_data:
             raise HTTPException(status_code=400, detail="DID does not appear to be restricted or encrypted_data is missing.")

        # 2. Decrypt using oydid
        # We need to pass the private key to oydid. 
        # The oydid CLI 'decrypt' command reads input from stdin (the ciphertext)
        # and options like --doc-enc for the private key.
        
        decrypt_args = ["decrypt"]
        if request.key_pwd:
             decrypt_args += ["--doc-pwd", request.key_pwd]
        
        # OYDID decrypt expects the key as --doc-enc or from a file. 
        # We'll use --doc-enc to pass the multibase private key directly.
        decrypt_args += ["--doc-enc", request.private_key]

        decrypt_result = run_oydid_command(decrypt_args, input_data=encrypted_data)
        
        if decrypt_result.returncode != 0:
            error_detail = getattr(decrypt_result, "error_msg", decrypt_result.stderr)
            raise HTTPException(status_code=400, detail=f"Decryption failed: {error_detail}")
            
        try:
            decrypted_payload = json.loads(decrypt_result.stdout)
            return {
                "did": did,
                "decrypted_payload": decrypted_payload,
                "restricted_to": doc.get("restricted_to")
            }
        except json.JSONDecodeError:
            return {
                "did": did,
                "decrypted_raw": decrypt_result.stdout.strip(),
                "restricted_to": doc.get("restricted_to")
            }

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON from DID resolver")

@router.get("/{did}")
async def read_did(did: str):
    """Read a DID Document"""
    # Sanitize DID to handle malformed URL params (e.g. &language=fr inside path)
    if "&" in did:
        did_original = did
        did = did.split("&")[0]
        print(f"DEBUG: Sanitized DID. Original: '{did_original}', Sanitized: '{did}'")
    else:
        print(f"DEBUG: DID received (no &): '{did}'")

    result = run_oydid_command(["read", did, "--json-output"])
    print(f"DEBUG: OYDID Read Result: ReturnCode={result.returncode}, Stderr='{result.stderr}', StdoutLen={len(result.stdout)}")
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=404, detail=f"DID not found or error: {error_detail}")
        
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}

@router.get("/resolve/{did}")
async def resolve_did(did: str):
    """Resolve a DID to its full W3C DID Document."""
    if "&" in did:
        did = did.split("&")[0]

    result = run_oydid_command(["read", did, "--w3c-did"])
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=404, detail=f"DID not found or error: {error_detail}")
        
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}

@router.get("/validate/{did}")
async def validate_did(did: str, public_key: str = Query(None, description="Public key multibase to check against the DID")):
    """
    Validate a DID. If public_key is provided, verifies if the user with this public key created or controls the DID.
    """
    if "&" in did:
        did = did.split("&")[0]

    result = run_oydid_command(["read", did, "--w3c-did"])
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=404, detail=f"DID not found or invalid: {error_detail}")
        
    try:
        did_doc = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON returned from resolver")
        
    response = {
        "valid": True,
        "did": did,
        "message": "DID is valid and resolvable."
    }
    
    if public_key:
        keys = []
        for vm in did_doc.get("verificationMethod", []):
            pk = vm.get("publicKeyMultibase")
            if pk:
                keys.append(pk)
        
        if public_key in keys:
             response["public_key_match"] = True
             response["message"] = f"The provided public key is authorized for this DID."
        else:
             response["public_key_match"] = False
             response["message"] = f"The provided public key was NOT found in the DID document."
             
    return response

@router.post("/update")
async def update_did(request: DidUpdateRequest):
    """Update a DID"""
    result = run_oydid_command(["update", request.did, "--json-output"], input_data=request.payload)
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=400, detail=f"Update failed: {error_detail}")
        
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}

@router.delete("/{did}")
async def revoke_did(did: str):
    """Revoke a DID"""
    result = run_oydid_command(["revoke", did, "--json-output"])
    
    if result.returncode != 0:
        error_detail = getattr(result, "error_msg", result.stderr)
        raise HTTPException(status_code=400, detail=f"Revocation failed: {error_detail}")
        
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}
