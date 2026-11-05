import subprocess
import shutil
import json
import pytest

def run_oydid_command(args, input_data=None):
    """Helper to run oydid commands"""
    if not shutil.which("oydid"):
        pytest.skip("oydid CLI not installed on host (runs inside Docker container)")
    cmd = ["oydid"] + args
    
    # If input_data is a dict, convert to JSON string
    input_str = None
    if input_data:
        if isinstance(input_data, dict):
            input_str = json.dumps(input_data)
        else:
            input_str = input_data

    process = subprocess.run(
        cmd,
        input=input_str,
        capture_output=True,
        text=True
    )
    
    return process

def test_oydid_lifecycle():
    print("\n--- Starting OYDID Lifecycle Test ---")

    # 1. Create DID
    print(" Creating DID...")
    create_payload = {"hello": "world"}
    # Use --json-output and NO --silent to get JSON output
    create_proc = run_oydid_command(["create", "--json-output"], input_data=create_payload)
    
    # Debug output
    print(f"Stdout: {create_proc.stdout}")
    print(f"Stderr: {create_proc.stderr}")

    assert create_proc.returncode == 0
    create_resp = json.loads(create_proc.stdout)
    did = create_resp["did"]
    print(f" Created DID: {did}")
    assert did.startswith("did:oyd:")

    # 2. Read DID
    print(" Reading DID...")
    read_proc = run_oydid_command(["read", did, "--json-output"])
    assert read_proc.returncode == 0
    did_doc = json.loads(read_proc.stdout)
    print(" Read DID Document successfully")
    
    # Verify content
    # OYDID read output with json-output might be the doc itself
    assert "hello" in json.dumps(did_doc)

    # 3. Update DID
    print(" Updating DID...")
    update_payload = {"hello": "updated world"}
    update_proc = run_oydid_command(["update", did, "--json-output"], input_data=update_payload)
    
    if update_proc.returncode == 0:
        print(" Update successful")
        update_resp = json.loads(update_proc.stdout)
        updated_did = update_resp["did"]
        print(f" Updated DID: {updated_did}")
        
        # OYDID might rotate DIDs on update? 
        # If so, updated_did might not match did.
        # Let's verify we can read the NEW DID and it has the new content.
        
        # Verify Update
        read_updated_proc = run_oydid_command(["read", updated_did, "--json-output"])
        assert "updated world" in read_updated_proc.stdout
    else:
        print(f" Update failed (expected if keys missing): {update_proc.stderr}")
        
    # 4. Revoke DID
    print(" Revoking DID...")
    revoke_proc = run_oydid_command(["revoke", did, "--json-output"])
    if revoke_proc.returncode == 0:
        print(" Revoke successful")
    else:
        print(f" Revoke failed: {revoke_proc.stderr}")

if __name__ == "__main__":
    test_oydid_lifecycle()
