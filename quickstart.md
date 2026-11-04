# OYDID Quickstart

Welcome to OYDID (Own Your Decentralized IDentifier)! This guide will get you up and running with OYDID using either the Command Line Interface (CLI) or the JavaScript library.

## What is OYDID?

OYDID provides a self-sustained environment for managing decentralized identifiers (DIDs). The `did:oyd` method links the identifier cryptographically to the DID Document and ensures resolution to the latest valid version through a public log.

## Option 1: CLI Quickstart

The easiest way to get started is using the CLI tool.

### Installation

**Via generic installer (requires Ruby 2.5.7+):**
```bash
sh -c "curl -fsSL https://raw.githubusercontent.com/OwnYourData/oydid/main/cli/install.sh | sh"
```

**Via Docker:**
```bash
docker run -it --rm oydeu/oydid-cli
```
*Note: To persist keys when using Docker, mount a volume:*
```bash
mkdir ~/.oydid
docker run -it --rm -v ~/.oydid:/home/oydid oydeu/oydid-cli
```

### Basic Usage

**1. Create a DID**
```bash
echo '{"hello":"world"}' | oydid create
```
*Output example:* `did:oyd:zQm...`

**2. Read a DID**
```bash
oydid read did:oyd:zQm...
```

**3. Update a DID**
```bash
echo '{"hello":"updated world"}' | oydid update did:oyd:zQm...
```

**4. Revoke a DID**
```bash
oydid revoke did:oyd:zQm...
```

**5. Encrypt and Decrypt a DID**
```bash
# Encrypt
echo '{"secret":"data"}' | oydid encrypt did:oyd:RecipientDID

# Decrypt
echo 'JWE_DATA' | oydid decrypt --doc-enc z1S5...RecipientPrivateKey
```

## Option 2: JavaScript Library Quickstart

If you are building a Node.js or web application, use the `oydid` npm package.

### Installation

```bash
npm install oydid
```

### Basic Usage (TypeScript/JavaScript)

```typescript
import { create, read, update, deactivate } from 'oydid';

async function main() {
    // 1. Create a DID
    console.log("Creating DID...");
    const newDid = await create({"hello": "world"});
    console.log(`Created: ${newDid.id}`);
    console.log(`Private Key: ${newDid.docKey}`);

    // 2. Read DID Document
    console.log("\nReading DID...");
    const didDoc = await read(newDid.id);
    console.log("Document Content:", didDoc.doc);

    // 3. Update DID
    console.log("\nUpdating DID...");
    const updatedDid = await update(newDid.id, {"hello": "Universe"});
    console.log(`Updated DID: ${updatedDid.id}`);

    // 4. Deactivate DID
    console.log("\nDeactivating DID...");
    await deactivate(newDid.id);
    console.log("DID Deactivated");
}

main().catch(console.error);
```

## Further Reading

- [Full CLI Documentation](cli/README.md)
- [Detailed Tutorial](tutorial/README.md)
- [API Documentation](https://api-docs.ownyourdata.eu/oydid/)
