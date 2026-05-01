# ODRL CLI Comprehensive Guide

The `odrl-cli` is a powerful command-line interface for interacting with the ODRL infrastructure. It allows you to manage groups, peers, policies, and various resources such as files, datasets, prompts, and variables via Decentralized Identifiers (DIDs).

## Table of Contents
- [Configuration](#configuration)
- [Identity & Context](#identity--context)
- [General Commands](#general-commands)
- [Group Management](#group-management)
- [Resource Management](#resource-management)
  - [Adding Resources](#adding-resources)
  - [Deleting Resources](#deleting-resources)
- [Policy Generation](#policy-generation)
- [Restricted Resources (Encryption & Decryption)](#restricted-resources-encryption--decryption)
- [Installation](#installation)

---

## Installation

You can install the ODRL CLI globally using `pip`:

```bash
cd odrl-infra
pip install -e .
```

After installation, the `odrl-cli` command will be available in your terminal.

---

## Configuration

The CLI relies on a configuration file named `odrl.config` to connect to the correct backend API. This file can be located in your current working directory or the parent directory of the script.

**Example `odrl.config`:**
```ini
[odrl]
url = http://10.147.18.90:8001/demo
```

    If the configuration file is missing, it will automatically fall back to the default URL `http://10.147.18.90:8001/demo`.

---

## Identity & Context

### Select Active Group
Set an active group context for your CLI session. Once an active group is selected, you can omit the `<group_did>` argument in commands that require a group (like `join`, `peers`, `listpolicy`, `add`, and `delete`); the CLI will automatically use the active group.
```bash
./bin/odrl-cli select <group_did>
```

### Whoami
View your identity context. The CLI now automatically detects your Master DID from your local wallet (`~/.odrl/did.json`), which is shared with tools like the `croissant-toolkit`.
```bash
./bin/odrl-cli whoami
```
**Example Output:**
```text
Master DID (Wallet): did:oyd:zQmcVHWDMeXtj273A9gNAnEG2EdrGEjtQiFuw9PncyVgs9z
User DID (Session):  did:oyd:zQmaqyhXuegiuT2QyTtbsUWABcDFThDAcrCNDALg36ZAecR
Active Group:        did:oyd:zQmcA93oUvBGm17hHvjrRFtwp3YhevgvpZ66tZwVe9qSoLJ
```

---

## General Commands

### Test Connection
Test if the CLI can successfully connect to the configured ODRL API.
```bash
./bin/odrl-cli test
```

### Resource Info
Fetch and nicely display detailed information about any resource (groups, users, prompts, files, datasets, etc.) using its DID. If no DID is provided, it defaults to resolving the currently active group.
```bash
./bin/odrl-cli info [did]
```

### Listing Global Resources
List all entities of a specific type registered on the network.

- **List Groups:** Shows all organizations/groups and their DIDs.
  ```bash
  ./bin/odrl-cli listgroups
  ```
- **List Files:** Shows all variables mapped as files.
  ```bash
  ./bin/odrl-cli listfiles
  ```
- **List Datasets:** Shows all registered datasets (Croissants).
  ```bash
  ./bin/odrl-cli listdatasets
  ```
- **List Policies:** Shows all policies associated with a specific group.
  ```bash
  ./bin/odrl-cli listpolicy [group_name_or_did]
  ```

---

## Group Management

### Create Group
Create a new ODRL group. This will prompt you for an optional description and generate a new Organization DID.
```bash
./bin/odrl-cli create <group_name>
```

### Join Group
Join an existing group using its DID. You will be prompted for your DID and the role you are assuming. The DID you provide will automatically be saved as your User DID for future operations.
```bash
./bin/odrl-cli join [group_did]
```

### List Peers
List all the current members (peers and resources) assigned to a group.
```bash
./bin/odrl-cli peers [group_did]
```

---

## Resource Management

The CLI supports managing various resources within a group, including `file`, `dataset`, `prompt`, `variable`, and nested `group` entities. Adding a resource generates a fresh DID on the network and links it securely to the parent group.

### Adding Resources

You can add resources interactively, or you can supply a text file to upload its contents directly.

**Syntax:**
```bash
./bin/odrl-cli add <resource_type> [group_did] [file_path]
```
*Note: The `[group_did]` argument can be omitted if you have an active group selected via `select`.*

**Resource Types:**
- `file`: Adds a file resource to the group. If `[file_path]` is provided, the file's content is used as the file description.
- `dataset`: Adds a dataset (Croissant). If `[file_path]` is provided, the file's content is used as the dataset description.
- `prompt`: Adds an LLM prompt. If `[file_path]` is provided, the file's content is injected directly as the prompt content.
- `variable`: Adds a variable. If `[file_path]` is provided, the file's content is used as the variable description.
- `group`: Nests a subgroup into the parent group.

**Examples:**
```bash
# Interactively add a prompt
./bin/odrl-cli add prompt did:oyd:example123

# Add a prompt by uploading a local text file
./bin/odrl-cli add prompt did:oyd:example123 ./tests/prompt.txt

# Add a prompt directly to the active group using a file
./bin/odrl-cli add prompt ./tests/prompt.txt

# Add a dataset definition
./bin/odrl-cli add dataset did:oyd:example123
```

### Deleting Resources

You can safely detach resources from a group and destroy their associated DIDs. The CLI will search the group for all items matching the requested resource type and present an interactive menu so you can select exactly which one to delete.

**Syntax:**
```bash
./bin/odrl-cli delete <resource_type> [group_did]
```
*Note: The `[group_did]` argument can be omitted if you have an active group selected via `select`.*

**Resource Types:**
- `file`, `dataset`, `prompt`, `variable`, `group`

**Example Workflow:**
```bash
$ ./bin/odrl-cli delete prompt did:oyd:example123
Deleting prompt from group did:oyd:example123
Available resources to delete:
1. did:oyd:zQmYa8T...
Enter the number of the prompt to delete (or 0 to cancel): 1
Successfully removed prompt from group!
Successfully deleted the prompt DID: did:oyd:zQmYa8T...
```

---

## Policy Generation

Generate standard ODRL JSON-LD policies for your groups. This creates an `odrl:Agreement` with the correct `dcterms` namespaces and permissions for your group members.

**Syntax:**
```bash
./bin/odrl-cli policy [group_did]
```
*Note: If no DID is provided, it uses the currently active group.*

---

## Restricted Resources (Encryption & Decryption)

Restricted DIDs allow you to share sensitive data that only a specific recipient (identified by their DID) can read. The CLI leverages your local wallet to make this process seamless.

### Encrypt a Prompt
You can encrypt a prompt for yourself or another recipient. The CLI is smart: if you only provide a file path, it assumes you are the recipient.

**Syntax:**
```bash
./bin/odrl-cli encrypt [recipient_did] <file_path>
```

**Examples:**
```bash
# Encrypt for yourself (automatically uses your Master DID)
./bin/odrl-cli encrypt ./tests/prompt

# Encrypt for a specific recipient
./bin/odrl-cli encrypt did:oyd:zQmRecipient ./tests/prompt
```

### Decrypt a Resource
Decrypt a restricted DID. To decrypt, you must be the recipient specified during encryption. The CLI will automatically use your private key from your local wallet.

**Syntax:**
```bash
./bin/odrl-cli decrypt <restricted_did> [private_key]
```

**Examples:**
```bash
# Decrypt using your wallet key (automatic)
./bin/odrl-cli decrypt did:oyd:zQmRestricted

# Decrypt using an explicit private key
./bin/odrl-cli decrypt did:oyd:zQmRestricted z1S5...
```
