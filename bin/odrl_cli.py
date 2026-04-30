#!/usr/bin/env python3

import argparse
import sys
import requests
import configparser
import os
import json
from urllib.parse import urlparse
from pathlib import Path

# Paths for local wallet (compatible with croissant-toolkit)
WALLET_DIR = Path.home() / ".odrl"
WALLET_FILE = WALLET_DIR / "did.json"

def get_wallet_data():
    if WALLET_FILE.exists():
        try:
            with open(WALLET_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def get_config_path():
    config_path = "odrl.config"
    script_dir_config = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "odrl.config")
    if os.path.exists(config_path):
        return config_path
    elif os.path.exists(script_dir_config):
        return script_dir_config
    return config_path

def get_config():
    config = configparser.ConfigParser()
    path = get_config_path()
    if os.path.exists(path):
        config.read(path)
    if "odrl" not in config:
        config["odrl"] = {}
    return config, path

def get_base_url():
    config, _ = get_config()
    return config["odrl"].get("url", "http://10.147.18.90:8001/demo")

def get_active_group():
    config, _ = get_config()
    return config["odrl"].get("active_group", None)

def set_active_group(group_did):
    config, path = get_config()
    config["odrl"]["active_group"] = group_did
    with open(path, "w") as f:
        config.write(f)

def get_user_did():
    config, _ = get_config()
    return config["odrl"].get("user_did", None)

def set_user_did(did):
    config, path = get_config()
    config["odrl"]["user_did"] = did
    with open(path, "w") as f:
        config.write(f)

def get_api_base():
    url = get_base_url()
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def parse_group_and_file(args_list):
    group_did = get_active_group()
    file_path = None
    if len(args_list) >= 2:
        group_did = args_list[0]
        file_path = args_list[1]
    elif len(args_list) == 1:
        arg = args_list[0]
        if os.path.exists(arg):
            file_path = arg
        elif not group_did:
            group_did = arg
        else:
            if arg.startswith("did:"):
                group_did = arg
            else:
                file_path = arg
    return group_did, file_path

def select_group(args):
    api_base = get_api_base()
    group_did = args.group
    print(f"Selecting group: {group_did}")
    try:
        res = requests.get(f"{api_base}/api/did/resolve/{group_did}", timeout=10)
        if res.status_code == 200:
            set_active_group(group_did)
            print(f"Successfully activated group {group_did}")
        else:
            print(f"Failed to fetch group {group_did}: {res.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def create_group(args):
    print(f"Creating new group: {args.group}")
    description = input("Enter description (optional): ").strip()
    
    api_base = get_api_base()
    url = f"{api_base}/api/groups/create"
    
    payload = {"name": args.group}
    if description:
        payload["description"] = description
        
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code in [200, 201]:
            print(f"Group created successfully:")
            print(response.json())
        else:
            print(f"Failed to create group. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def join_group(args):
    api_base = get_api_base()
    group_did = args.group or get_active_group()
    if not group_did:
        print("Error: No group provided and no active group selected.")
        return
    
    print(f"Joining group: {group_did}")
    try:
        res = requests.get(f"{api_base}/api/did/resolve/{group_did}", timeout=10)
        if res.status_code != 200:
            print(f"Failed to fetch group: {res.status_code}")
            return
            
        data = res.json()
        payload = data.get("service", [{}])[0].get("payload", {})
        group_name = payload.get("name", group_did)
        members = payload.get("members", payload.get("hasMember", []))
        
        member_did = input("Enter your DID to join: ").strip()
        role = input("Enter role (default: Member): ").strip() or "Member"
        
        if member_did:
            set_user_did(member_did)
        
        members.append({"member": member_did, "role": role})
        
        update_payload = {
            "name": group_name,
            "description": payload.get("description", ""),
            "members": members
        }
        
        update_res = requests.put(f"{api_base}/api/groups/{group_did}", json=update_payload, timeout=10)
        if update_res.status_code == 200:
            print("Successfully joined group!")
            print(update_res.json())
        else:
            print(f"Failed to join group: {update_res.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def list_peers(args):
    api_base = get_api_base()
    group_did = args.group or get_active_group()
    if not group_did:
        print("Error: No group provided and no active group selected.")
        return
    print(f"Listing peers in group: {group_did}")
    try:
        res = requests.get(f"{api_base}/api/did/resolve/{group_did}", timeout=10)
        if res.status_code == 200:
            payload = res.json().get("service", [{}])[0].get("payload", {})
            members = payload.get("members", payload.get("hasMember", []))
            if not members:
                print("No peers found.")
            else:
                for idx, m in enumerate(members, 1):
                    print(f"{idx}. {m.get('member')} (Role: {m.get('role')})")
        else:
            print(f"Failed to fetch group: {res.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def list_groups(args):
    api_base = get_api_base()
    print("Listing all groups...")
    try:
        res = requests.get(f"{api_base}/api/oac/search", params={"q": "Organization", "collection": "dids"}, timeout=10)
        if res.status_code == 200:
            groups = res.json()
            for g in groups:
                print(f"- {g.get('json_ld', {}).get('name', 'Unknown')} (DID: {g.get('did')})")
        else:
            print(f"Failed to list groups: {res.text}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def list_files(args):
    api_base = get_api_base()
    print("Listing all files (variables)...")
    try:
        res = requests.get(f"{api_base}/api/oac/search", params={"q": "", "collection": "variables"}, timeout=10)
        if res.status_code == 200:
            files = res.json()
            for f in files:
                name = f.get('json_ld', {}).get('name', 'Unknown')
                print(f"- {name} (DID: {f.get('did')})")
        else:
            print(f"Failed to list files: {res.text}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def list_datasets(args):
    api_base = get_api_base()
    print("Listing all datasets (croissants)...")
    try:
        res = requests.get(f"{api_base}/api/oac/search", params={"q": "", "collection": "croissant"}, timeout=10)
        if res.status_code == 200:
            datasets = res.json()
            for d in datasets:
                name = d.get('json_ld', {}).get('name', 'Unknown')
                print(f"- {name} (DID: {d.get('did')})")
        else:
            print(f"Failed to list datasets: {res.text}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def list_policy(args):
    api_base = get_api_base()
    group = args.group or get_active_group()
    if not group:
        print("Error: No group provided and no active group selected.")
        return
    print(f"Listing policy for group: {group}")
    try:
        res = requests.get(f"{api_base}/api/oac/search", params={"q": group, "collection": "policy"}, timeout=10)
        if res.status_code == 200:
            policies = res.json()
            if not policies:
                print("No policies found.")
            for p in policies:
                uid = p.get('json_ld', {}).get('odrl:uid', 'Unknown')
                print(f"- Policy UID: {uid} (DID: {p.get('did')})")
        else:
            print(f"Failed to list policy: {res.text}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def add_resource(args):
    api_base = get_api_base()
    resource_type = args.resource_type
    group_did, file_path = parse_group_and_file(args.args)
    if not group_did:
        print("Error: No group provided and no active group selected.")
        return
        
    print(f"Adding new {resource_type} to group {group_did}")
    
    if resource_type == "file":
        name = input("Enter file name: ").strip()
        if file_path and os.path.exists(file_path):
            with open(file_path, "r") as f:
                desc = f.read()
            print(f"Read content from {file_path}")
        else:
            desc = input("Enter description: ").strip()
        payload = {"payload": {"type": "File", "name": name, "description": desc}, "collection": "variables"}
        url = f"{api_base}/api/did/create"
        
    elif resource_type == "dataset":
        url_input = input("Enter dataset URL (optional): ").strip()
        if file_path and os.path.exists(file_path):
            with open(file_path, "r") as f:
                desc = f.read()
            print(f"Read description from {file_path}")
        else:
            desc = input("Enter description: ").strip()
        payload = {"description": desc}
        if url_input:
            payload["url"] = url_input
        url = f"{api_base}/api/croissants/create"
        
    elif resource_type == "group":
        name = input("Enter subgroup name: ").strip()
        desc = input("Enter subgroup description: ").strip()
        payload = {"name": name, "description": desc}
        url = f"{api_base}/api/groups/create"
        
    elif resource_type == "prompt":
        name = input("Enter prompt name: ").strip()
        if file_path and os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
            print(f"Read content from {file_path}")
        else:
            content = input("Enter prompt content: ").strip()
        payload = {"payload": {"type": "Prompt", "name": name, "content": content}, "collection": "prompts"}
        url = f"{api_base}/api/did/create"
        
    elif resource_type == "variable":
        name = input("Enter variable name: ").strip()
        if file_path and os.path.exists(file_path):
            with open(file_path, "r") as f:
                desc = f.read()
            print(f"Read description from {file_path}")
        else:
            desc = input("Enter description: ").strip()
        unit = input("Enter unit: ").strip()
        payload = {"name": name, "description": desc, "unit": unit}
        url = f"{api_base}/api/variables/create"

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code in [200, 201]:
            new_did = res.json().get("did")
            print(f"Created new {resource_type} with DID: {new_did}")
            
            group_res = requests.get(f"{api_base}/api/did/resolve/{group_did}", timeout=10)
            if group_res.status_code == 200:
                data = group_res.json()
                group_payload = data.get("service", [{}])[0].get("payload", {})
                group_name = group_payload.get("name", group_did)
                members = group_payload.get("members", group_payload.get("hasMember", []))
                
                members.append({"member": new_did, "role": resource_type.capitalize()})
                
                update_payload = {
                    "name": group_name,
                    "description": group_payload.get("description", ""),
                    "members": members
                }
                
                update_res = requests.put(f"{api_base}/api/groups/{group_did}", json=update_payload, timeout=10)
                if update_res.status_code == 200:
                    print(f"Successfully included {resource_type} in group!")
                else:
                    print(f"Failed to update group: {update_res.text}")
            else:
                print(f"Failed to fetch group {group_did}: {group_res.status_code}")
        else:
            print(f"Failed to create {resource_type}. Status: {res.status_code}, Response: {res.text}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def delete_resource(args):
    api_base = get_api_base()
    resource_type = args.resource_type
    group_did, _ = parse_group_and_file(args.args)
    if not group_did:
        print("Error: No group provided and no active group selected.")
        return
    
    print(f"Deleting {resource_type} from group {group_did}")
    try:
        group_res = requests.get(f"{api_base}/api/did/resolve/{group_did}", timeout=10)
        if group_res.status_code != 200:
            print(f"Failed to fetch group {group_did}: {group_res.status_code}")
            return
            
        data = group_res.json()
        group_payload = data.get("service", [{}])[0].get("payload", {})
        group_name = group_payload.get("name", group_did)
        members = group_payload.get("members", group_payload.get("hasMember", []))
        
        target_role = resource_type.capitalize()
        matching_members = [m for m in members if m.get("role") == target_role]
        
        if not matching_members:
            print(f"No resources of type '{resource_type}' found in group.")
            return
            
        print("Available resources to delete:")
        for idx, m in enumerate(matching_members, 1):
            print(f"{idx}. {m.get('member')}")
            
        choice = input(f"Enter the number of the {resource_type} to delete (or 0 to cancel): ").strip()
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(matching_members):
            print("Cancelled.")
            return
            
        member_to_remove = matching_members[int(choice)-1]
        resource_did = member_to_remove["member"]
        
        # 1. Remove from group
        members.remove(member_to_remove)
        update_payload = {
            "name": group_name,
            "description": group_payload.get("description", ""),
            "members": members
        }
        
        update_res = requests.put(f"{api_base}/api/groups/{group_did}", json=update_payload, timeout=10)
        if update_res.status_code == 200:
            print(f"Successfully removed {resource_type} from group!")
        else:
            print(f"Failed to update group: {update_res.text}")
            return
            
        # 2. Delete the DID completely
        delete_res = requests.delete(f"{api_base}/api/did/{resource_did}", timeout=10)
        if delete_res.status_code in [200, 204]:
            print(f"Successfully deleted the {resource_type} DID: {resource_did}")
        else:
            print(f"Failed to delete the DID. Status: {delete_res.status_code}, Response: {delete_res.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def whoami(args):
    active_group = get_active_group()
    user_did = get_user_did()
    api_base = get_api_base()
    
    wallet = get_wallet_data()
    master_did = wallet.get("did") if wallet else "Not initialized"
    print(f"Master DID (Wallet): {master_did}")

    if user_did:
        print(f"User DID (Session):  {user_did}")
        try:
            res = requests.get(f"{api_base}/api/did/resolve/{user_did}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                name = data.get("service", [{}])[0].get("payload", {}).get("name")
                if name:
                    print(f"User Name:    {name}")
        except Exception:
            pass
    else:
        print("User DID:     Not set (join a group or configure 'user_did' in odrl.config)")
        
    if active_group:
        print(f"Active Group: {active_group}")
        try:
            res = requests.get(f"{api_base}/api/did/resolve/{active_group}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                name = data.get("service", [{}])[0].get("payload", {}).get("name")
                if name:
                    print(f"Group Name:   {name}")
        except Exception:
            pass
    else:
        print("Active Group: None selected (use 'odrl-cli select <group_did>')")

def info_resource(args):
    api_base = get_api_base()
    did = args.did or get_active_group()
    if not did:
        print("Error: Please provide a DID or select an active group.")
        return
        
    try:
        res = requests.get(f"{api_base}/api/did/resolve/{did}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            payload = data.get("service", [{}])[0].get("payload")
            
            if payload:
                for key, value in payload.items():
                    if isinstance(value, list):
                        print(f"{key.capitalize()}:")
                        for item in value:
                            if isinstance(item, dict):
                                print(f"  - {', '.join(f'{k}={v}' for k,v in item.items())}")
                            else:
                                print(f"  - {item}")
                    elif isinstance(value, dict):
                        print(f"{key.capitalize()}:")
                        for k, v in value.items():
                            print(f"  {k}: {v}")
                    else:
                        print(f"{key.capitalize()}: {value}")
            else:
                print("No standard payload found. Raw data:")
                print(json.dumps(data, indent=2))
        else:
            print(f"Failed to fetch info for {did}. Status: {res.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def generate_policy(args):
    api_base = get_api_base()
    group_did = args.group or get_active_group()
    if not group_did:
        print("Error: No group provided and no active group selected.")
        return

    try:
        res = requests.get(f"{api_base}/api/did/resolve/{group_did}", timeout=10)
        if res.status_code != 200:
            print(f"Failed to fetch group {group_did}: {res.status_code}")
            return

        data = res.json()
        payload = data.get("service", [{}])[0].get("payload", {})
        members = payload.get("members", payload.get("hasMember", []))

        policy = {
            "@context": [
                "http://www.w3.org/ns/odrl.jsonld",
                {
                    "dcterms": "http://purl.org/dc/terms/"
                }
            ],
            "@type": "odrl:Agreement",
            "@id": f"https://odrl.dev.codata.org/policy/{group_did}",
            "odrl:permission": []
        }

        for m in members:
            member_did = m.get("member")
            if member_did:
                policy["odrl:permission"].append({
                    "odrl:target": group_did,
                    "odrl:assigner": group_did,
                    "odrl:assignee": member_did,
                    "odrl:action": "odrl:use"
                })

        print(json.dumps(policy, indent=2))
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")

def restrict_prompt(args):
    api_base = get_api_base()
    
    arg1 = args.target_did
    arg2 = args.file
    
    target_did = None
    content_file = None
    
    # Smart detection: if arg1 looks like a file and arg2 is None, use arg1 as file
    if arg1 and not arg2:
        if os.path.exists(arg1) or "." in arg1 or "/" in arg1:
            content_file = arg1
        else:
            target_did = arg1
    else:
        target_did = arg1
        content_file = arg2
    
    if not target_did:
        wallet = get_wallet_data()
        if wallet:
            target_did = wallet.get("did")
            print(f"Using Master DID from wallet as recipient: {target_did}")
        else:
            print("Error: No recipient DID provided and no local wallet found.")
            return
    
    if content_file and os.path.exists(content_file):
        with open(content_file, "r") as f:
            content = f.read()
    else:
        content = input("Enter restricted prompt content: ").strip()
        
    payload = {
        "payload": {
            "type": "Prompt",
            "content": content
        },
        "target_did": target_did,
        "collection": "prompts"
    }
    
    try:
        # Note: /api/did/create/restricted is usually at the base API level
        # We'll use the base URL (without /demo) as in other resolution calls
        parsed_base = urlparse(get_base_url())
        api_root = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        res = requests.post(f"{api_root}/api/did/create/restricted", json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            print(f"Created restricted prompt!")
            print(f"DID:         {data.get('did')}")
            
            keys = data.get('keys', {})
            print(f"Private Key: {keys.get('private_key')}")
            print(f"Target DID:  {target_did}")
            print("\nIMPORTANT: Securely share the Private Key with the recipient.")
        else:
            print(f"Failed to create restricted prompt: {res.status_code}")
            print(res.text)
    except Exception as e:
        print(f"Error: {e}")

def decrypt_resource(args):
    did = args.did
    private_key = args.private_key
    
    if not private_key:
        wallet = get_wallet_data()
        if wallet:
            private_key = wallet.get("keys", {}).get("private_key")
            print("Using private key from local wallet...")
        else:
            print("Error: No private key provided and no local wallet found.")
            return
            
    payload = {
        "did": did,
        "private_key": private_key
    }
    
    try:
        parsed_base = urlparse(get_base_url())
        api_root = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        res = requests.post(f"{api_root}/api/did/resolve/restricted", json=payload, timeout=10)
        if res.status_code == 200:
            print("Successfully decrypted resource!")
            data = res.json()
            decrypted = data.get("decrypted_payload", {})
            
            # The payload might be a string or a dict
            if isinstance(decrypted, dict):
                content = decrypted.get("content") or decrypted.get("secret")
                if content:
                    print(f"\nDecrypted Content:\n{content}")
                else:
                    print("\nDecrypted Data:")
                    print(json.dumps(decrypted, indent=2))
            else:
                print(f"\nDecrypted Data: {decrypted}")
        else:
            print(f"Decryption failed: {res.status_code}")
            print(res.text)
    except Exception as e:
        print(f"Error: {e}")

def test_connection(args):
    url = get_base_url()
    print(f"Testing connection to ODRL API at {url} ...")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"Successfully connected! (Status Code: {response.status_code} at {url})")
        else:
            print(f"Connected, but received status code: {response.status_code} at {url}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to API. Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="ODRL Infrastructure CLI")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # select
    parser_select = subparsers.add_parser("select", help="Select active group")
    parser_select.add_argument("group", help="Group DID")

    # whoami
    parser_whoami = subparsers.add_parser("whoami", help="Show current user DID and active group")

    # info
    parser_info = subparsers.add_parser("info", help="Show information about a specific resource")
    parser_info.add_argument("did", nargs="?", help="DID of the resource")

    # policy
    parser_policy = subparsers.add_parser("policy", help="Generate ODRL policy for a group")
    parser_policy.add_argument("group", nargs="?", help="Group DID")

    # restrict
    parser_restrict = subparsers.add_parser("restrict", help="Manage restricted (encrypted) resources")
    restrict_subparsers = parser_restrict.add_subparsers(dest="subcommand", help="Resource type to restrict")
    
    parser_restrict_prompt = restrict_subparsers.add_parser("prompt", help="Create a restricted prompt")
    parser_restrict_prompt.add_argument("target_did", nargs="?", help="Recipient DID who can decrypt the content (defaults to wallet DID)")
    parser_restrict_prompt.add_argument("file", nargs="?", help="Local file containing prompt content")

    # encrypt (alias for restrict prompt)
    parser_encrypt = subparsers.add_parser("encrypt", help="Encrypt a prompt for a recipient (alias for restrict prompt)")
    parser_encrypt.add_argument("target_did", nargs="?", help="Recipient DID who can decrypt the content (defaults to wallet DID)")
    parser_encrypt.add_argument("file", nargs="?", help="Local file containing prompt content")

    # decrypt
    parser_decrypt = subparsers.add_parser("decrypt", help="Decrypt a restricted resource")
    parser_decrypt.add_argument("did", help="DID of the restricted resource")
    parser_decrypt.add_argument("private_key", nargs="?", help="Recipient's private key (defaults to wallet key)")

    # create
    parser_create = subparsers.add_parser("create", help="Create new group")
    parser_create.add_argument("group", help="Name of the group to create")
    
    # join
    parser_join = subparsers.add_parser("join", help="Join group")
    parser_join.add_argument("group", nargs="?", help="Name of the group to join")

    # peers
    parser_peers = subparsers.add_parser("peers", help="Show peers in group")
    parser_peers.add_argument("group", nargs="?", help="Name of the group")

    # listgroups
    parser_listgroups = subparsers.add_parser("listgroups", help="Show all groups")

    # listfiles
    parser_listfiles = subparsers.add_parser("listfiles", help="Show all files")

    # listdatasets
    parser_listdatasets = subparsers.add_parser("listdatasets", help="Show all datasets")

    # listpolicy
    parser_listpolicy = subparsers.add_parser("listpolicy", help="Show policy for a specific group")
    parser_listpolicy.add_argument("group", nargs="?", help="Name of the group")

    # add
    parser_add = subparsers.add_parser("add", help="Add a resource to a group")
    add_subparsers = parser_add.add_subparsers(dest="resource_type", required=True, help="Type of resource to add")

    add_file = add_subparsers.add_parser("file", help="Add a file to group")
    add_file.add_argument("args", nargs="*", help="[group] [file]")

    add_dataset = add_subparsers.add_parser("dataset", help="Add a dataset to group")
    add_dataset.add_argument("args", nargs="*", help="[group] [file]")

    add_group = add_subparsers.add_parser("group", help="Add a subgroup to group")
    add_group.add_argument("args", nargs="*", help="[group]")

    add_prompt = add_subparsers.add_parser("prompt", help="Add a prompt to group")
    add_prompt.add_argument("args", nargs="*", help="[group] [file]")

    add_variable = add_subparsers.add_parser("variable", help="Add a variable to group")
    add_variable.add_argument("args", nargs="*", help="[group] [file]")

    # delete
    parser_delete = subparsers.add_parser("delete", help="Delete a resource from a group")
    delete_subparsers = parser_delete.add_subparsers(dest="resource_type", required=True, help="Type of resource to delete")

    delete_file = delete_subparsers.add_parser("file", help="Delete a file from group")
    delete_file.add_argument("args", nargs="*", help="[group]")

    delete_dataset = delete_subparsers.add_parser("dataset", help="Delete a dataset from group")
    delete_dataset.add_argument("args", nargs="*", help="[group]")

    delete_group = delete_subparsers.add_parser("group", help="Delete a subgroup from group")
    delete_group.add_argument("args", nargs="*", help="[group]")

    delete_prompt = delete_subparsers.add_parser("prompt", help="Delete a prompt from group")
    delete_prompt.add_argument("args", nargs="*", help="[group]")

    delete_variable = delete_subparsers.add_parser("variable", help="Delete a variable from group")
    delete_variable.add_argument("args", nargs="*", help="[group]")

    # test
    parser_test = subparsers.add_parser("test", help="Test connection to ODRL APIs")

    args = parser.parse_args()

    if args.command == "select":
        select_group(args)
    elif args.command == "whoami":
        whoami(args)
    elif args.command == "info":
        info_resource(args)
    elif args.command == "policy":
        generate_policy(args)
    elif args.command == "restrict":
        if args.subcommand == "prompt":
            restrict_prompt(args)
        else:
            parser_restrict.print_help()
    elif args.command == "encrypt":
        restrict_prompt(args)
    elif args.command == "decrypt":
        decrypt_resource(args)
    elif args.command == "create":
        create_group(args)
    elif args.command == "join":
        join_group(args)
    elif args.command == "peers":
        list_peers(args)
    elif args.command == "listgroups":
        list_groups(args)
    elif args.command == "listfiles":
        list_files(args)
    elif args.command == "listdatasets":
        list_datasets(args)
    elif args.command == "listpolicy":
        list_policy(args)
    elif args.command == "add":
        add_resource(args)
    elif args.command == "delete":
        delete_resource(args)
    elif args.command == "test":
        test_connection(args)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
