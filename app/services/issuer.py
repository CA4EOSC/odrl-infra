import os
import json
from .oydid import run_oydid_command

ISSUER_DID_FILE = "issuer_did.json"

_issuer_did = None

def get_issuer_did():
    global _issuer_did
    if _issuer_did:
        return _issuer_did
        
    location = os.getenv("OYDID_LOCATION", ".")
    
    if os.path.exists(ISSUER_DID_FILE):
        try:
            with open(ISSUER_DID_FILE, "r") as f:
                data = json.load(f)
                did = data["did"]
                
                # Check if private key exists
                prefix = did.split(":")[-1][:10]
                key_file = os.path.join(location, f"{prefix}_private_key.enc")
                
                if os.path.exists(key_file):
                    _issuer_did = did
                    print(f"Loaded Issuer DID: {_issuer_did}")
                    return _issuer_did
                else:
                    print(f"Warning: Issuer DID {did} found in {ISSUER_DID_FILE} but private key {key_file} is missing.")
        except Exception as e:
            print(f"Error loading issuer DID: {e}")

    print("Creating/Re-creating Issuer DID...", flush=True)
    # Initialize with a basic DID
    result = run_oydid_command(["create", "--json-output"], input_data={"type": "Issuer"})
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            _issuer_did = data["did"]
            # Save DID info
            with open(ISSUER_DID_FILE, "w") as f:
                json.dump(data, f)
            print(f"Created Issuer DID: {_issuer_did}", flush=True)
        except Exception as e:
            print(f"Failed to parse issuer creation: {e}")
    else:
        print(f"Failed to create issuer DID: {result.stderr}")
            
    return _issuer_did

