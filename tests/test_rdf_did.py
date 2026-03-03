import requests
import json
import time

BASE_URL = "http://localhost:8001/api"
TURTLE_URL = "https://raw.githubusercontent.com/4tikhonov/the-minority-report/refs/heads/main/data/hips.ttl"

def test_rdf_did():
    print("--- Testing RDF Turtle DID Support ---")
    
    # 1. Create DID from Turtle URL
    print(f"\n[GET] /did/create_from_url?url={TURTLE_URL}")
    did = None
    try:
        resp = requests.get(f"{BASE_URL}/did/create_from_url", params={"url": TURTLE_URL})
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            did = data.get("did")
            stored = data.get("stored_payload")
            print(f"SUCCESS: Created DID: {did}")
            print(f"Payload Title: {stored.get('title')}")
            
            if stored.get("is_rdf"):
                print("VALIDATION: Recognized as RDF.")
            else:
                print("FAILURE: Not recognized as RDF.")
        else:
            print(f"FAILURE: {resp.text}")
            return
    except Exception as e:
        print(f"ERROR: {e}")
        return

    # Wait a bit for indexing? (usually instant for local OYDID)
    time.sleep(1)

    # 2. Share with Language 'fr' (French)
    # The file has: skos:prefLabel "Interoperability of public services"@en, "Interopérabilité des services publics"@fr
    print(f"\n[GET] /did/share/{did}?language=fr")
    try:
        resp = requests.get(f"{BASE_URL}/did/share/{did}", params={"language": "fr"})
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            payload = resp.json()
            print(f"Title: {payload.get('title')}")
            props = payload.get("properties", {})
            print(f"Properties (fr): {json.dumps(props, indent=2)}")
            
            # Check for Paired Output
            concepts = payload.get("concepts", [])
            print(f"DEBUG: Found {len(concepts)} concepts with English/French pairs.")
            if concepts:
                print(f"DEBUG: First concept sample: {json.dumps(concepts[0], indent=2)}")
            
            found = False
            for c in concepts:
                en_title = c.get("en", "")
                fr_title = c.get("fr", "")
                
                if "Supply Chain" in en_title and "approvisionnement" in fr_title.lower():
                     found = True
                     print(f"DEBUG: Found match: {en_title} -> {fr_title}")
                     break
            
            if found:
                print("VALIDATION: Retrieved expected English-French pair.")
            else:
                print("FAILURE: Did not retrieve expected English-French pair.")
    except Exception as e:
        print(f"ERROR: {e}")

    # 3. Share with Language 'en' (English)
    print(f"\n[GET] /did/share/{did}?language=en")
    try:
        resp = requests.get(f"{BASE_URL}/did/share/{did}", params={"language": "en"})
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            payload = resp.json()
            concepts = payload.get("concepts", [])
            
            found = False
            for c in concepts:
                 en_title = c.get("en", "")
                 if "Interoperability" in en_title or "Disaster" in en_title:
                     found = True
                     break
            
            if found:
                 print("VALIDATION: Retrieved expected English pair")
            else:
                 print("FAILURE: Did not retrieve expected English pair")
    except Exception as e:
        print(f"ERROR: {e}")
                 
    # 4. Share with Language Tag in DID (e.g. @fr)
    print(f"\n[GET] /did/share/{did}@fr")
    try:
        # Note: requests might encode the @, so we test if the API handles it
        resp = requests.get(f"{BASE_URL}/did/share/{did}@fr")
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            payload = resp.json()
            concepts = payload.get("concepts", [])
            # Should have the same result as ?language=fr
            found = False
            for c in concepts:
                if "approvisionnement" in c.get("fr", "").lower():
                    found = True
                    break
            
            if found:
                 print("VALIDATION: Retrieved expected French pair via @fr syntax")
            else:
                 print("FAILURE: Did not retrieve French via @fr syntax")
        else:
             print(f"FAILURE: {resp.text}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_rdf_did()
