# ODRL Infrastructure CLI (`odrl_cli.py`) Demo & Usage Guide

This guide provides a detailed demonstration on how to use the `odrl_cli.py` script to interact with the Open Digital Rights Language (ODRL) infrastructure. 

## Prerequisites
Before you start, ensure that your CLI configuration or environment points to the correct ODRL API. The script typically relies on a local wallet file located at `~/.odrl/did.json` and optionally a local configuration `odrl.config`.

## Basic Commands

### 1. Test Connection
To ensure you can reach the ODRL API endpoints:
```bash
./bin/odrl_cli.py test
```
*Expected Output:*
> Testing connection to ODRL API at http://10.147.18.90:8001/demo ...
> Successfully connected! (Status Code: 200 at http://10.147.18.90:8001/demo)

### 2. Check Identity & Current State (`whoami`)
See which DID (Decentralized Identifier) is registered as your Master DID, your Session User DID, and your currently selected active group.
```bash
./bin/odrl_cli.py whoami
```
*Example Output:*
> Master DID (Wallet): did:oyd:zQmcVHWDMeXtj273A9gNAnEG2EdrGEjtQiFuw9PncyVgs9z
> User DID (Session):  z1S5S5y2SVSwEXysWTey8ap39JUNG75MMUhmtJYwWaasB8jm
> Active Group: None selected (use 'odrl-cli select <group_did>')

---

## Group Management

### 3. List All Available Groups
To view the groups available within the ODRL infrastructure:
```bash
./bin/odrl_cli.py listgroups
```
*Example Output:*
> Listing all groups...
> - Home - Metadata Center (DID: did:oyd:zQmXyvan7PGSqyFTYeVGeFG8RbnnbfwWNcSoJS6AfEw17nm)
> - ClimateAdapt4EOSC_Project (DID: did:oyd:zQmR9CZUoFqBAt9TyPqMrjs3KBXBky3LPJd8UvMuPTASdvz)

### 4. Select an Active Group
Once you identify the DID of the group you want to work within, make it active:
```bash
./bin/odrl_cli.py select did:oyd:zQmR9CZUoFqBAt9TyPqMrjs3KBXBky3LPJd8UvMuPTASdvz
```

### 5. Inspect Group or Resource Info
You can inspect the details of the active group (or any resource DID):
```bash
./bin/odrl_cli.py info did:oyd:zQmR9CZUoFqBAt9TyPqMrjs3KBXBky3LPJd8UvMuPTASdvz
```
*Example Output:*
> Name: ClimateAdapt4EOSC_Project
> Role: Skill Consumer
> Created_at: 7992bea2
> Agent: Antigravity AI
> Description: Main project DID

### 6. View Peers in the Active Group
To see members/peers belonging to the currently active group:
```bash
./bin/odrl_cli.py peers
```
Or specify the group DID:
```bash
./bin/odrl_cli.py peers did:oyd:zQmR9CZUoFqBAt9TyPqMrjs3KBXBky3LPJd8UvMuPTASdvz
```

### 7. Create or Join a Group
- **Create:** `./bin/odrl_cli.py create "My New Group"`
- **Join:** `./bin/odrl_cli.py join <group_did>` (will prompt for your DID to join with).

---

## Resource Management (Datasets, Files, Policies)

### 8. List Datasets and Policies
View all datasets (Croissants) or policies:
```bash
./bin/odrl_cli.py listdatasets
./bin/odrl_cli.py listpolicy
```
*Listing Policy Example:*
> Listing policy for group: did:oyd:zQmR9CZUoFqBAt9TyPqMrjs3KBXBky3LPJd8UvMuPTASdvz
> - Policy UID: 5f5ae99d-2e15-43c0-bd91-6f83d3b38b04 (DID: did:oyd:zQmVFZ6fQTsb4qDUmW4dmNHMu6dFuiWaKjzs6hJyEijT5A3)

### 9. Add Resources to a Group
You can add various types of resources (file, dataset, prompt, group, variable) to the selected active group.
```bash
# Add a dataset
./bin/odrl_cli.py add dataset

# Add a file (will prompt for file name and description/content)
./bin/odrl_cli.py add file
```

---

## Secure/Restricted Actions

### 10. Restrict (Encrypt) a Prompt
If you want to create a restricted/encrypted prompt for a specific target DID, use `encrypt` or `restrict prompt`.
```bash
# Syntax: ./bin/odrl_cli.py encrypt <recipient_did> [file_path]
./bin/odrl_cli.py encrypt did:oyd:zQmRecipient... ./prompt.txt
```
*This command will output a restricted resource DID and a Private Key for decryption.*

### 11. Decrypt a Resource
You can resolve and decrypt a restricted DID if you hold the required private key.
```bash
# Syntax: ./bin/odrl_cli.py decrypt <restricted_did> [private_key]
./bin/odrl_cli.py decrypt did:oyd:zQmRestricted...
```
*(If the private key is not provided, the CLI will attempt to use the key from your local `~/.odrl/did.json` wallet).*
