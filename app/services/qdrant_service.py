import os
import json
from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastembed import TextEmbedding
from typing import List, Dict, Any

class QdrantService:
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.collections = ["policy", "prompts", "variables", "croissant", "dids", "groups", "bookmarks"]
        self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.encoder = TextEmbedding()
        self._ensure_collections()

    def _ensure_collections(self):
        # Get embedding dimension once
        example_embedding = list(self.encoder.embed(["test"]))[0]
        dimension = len(example_embedding)

        for coll in self.collections:
            try:
                self.client.get_collection(coll)
            except Exception:
                # Create collection if it doesn't exist
                self.client.create_collection(
                    collection_name=coll,
                    vectors_config=models.VectorParams(
                        size=dimension,
                        distance=models.Distance.COSINE
                    )
                )
                print(f"Created Qdrant collection: {coll}")

    def upsert_document(self, did: str, payload: Dict[str, Any], collection: str = None):
        # Determine collection if not explicitly provided
        if not collection:
            collection = self._determine_collection(payload)
            
        # Ensure collection exists
        if collection not in self.collections:
            try:
                self.client.get_collection(collection)
                self.collections.append(collection)
            except Exception:
                example_embedding = list(self.encoder.embed(["test"]))[0]
                dimension = len(example_embedding)
                self.client.create_collection(
                    collection_name=collection,
                    vectors_config=models.VectorParams(
                        size=dimension,
                        distance=models.Distance.COSINE
                    )
                )
                self.collections.append(collection)
                print(f"Created Qdrant collection dynamically: {collection}")
        
        # Convert payload to a text string for embedding
        text_content = self._extract_text_content(payload)
        embeddings = list(self.encoder.embed([text_content]))[0]
        
        self.client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=self._did_to_id(did),
                    vector=embeddings.tolist(),
                    payload={
                        "did": did,
                        "json_ld": payload,
                        "text": text_content
                    }
                )
            ]
        )
        print(f"Upserted DID {did} to Qdrant collection: {collection}")

    def search_documents(self, query_text: str, collection: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        # If collection is "all" or None, search across all collections
        collections_to_search = [collection] if collection and collection in self.collections else self.collections

        try:
            query_vector = list(self.encoder.embed([query_text]))[0]
            all_results = []
            
            for coll in collections_to_search:
                try:
                    # Use query_points which is the modern and more robust API
                    search_result = self.client.query_points(
                        collection_name=coll,
                        query=query_vector.tolist(),
                        limit=limit,
                        with_payload=True
                    ).points
                    
                    for hit in search_result:
                        all_results.append({
                            "did": hit.payload.get("did"),
                            "json_ld": hit.payload.get("json_ld"),
                            "score": hit.score,
                            "collection": coll
                        })
                except AttributeError:
                    # Fallback to search if query_points is missing
                    if hasattr(self.client, "search"):
                        search_result = self.client.search(
                            collection_name=coll,
                            query_vector=query_vector.tolist(),
                            limit=limit,
                            with_payload=True
                        )
                        for hit in search_result:
                            all_results.append({
                                "did": hit.payload.get("did"),
                                "json_ld": hit.payload.get("json_ld"),
                                "score": hit.score,
                                "collection": coll
                            })
                            
            # Sort by score descending and return top 'limit' results
            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:limit]
            
        except Exception as e:
            print(f"ERROR in search_documents: {e}")
            raise e

    def _determine_collection(self, payload: Dict[str, Any]) -> str:
        # Logic to route payload to the correct collection
        
        # 1. Variables
        if payload.get("type") == "Variable":
            return "variables"
        
        # 2. Prompts
        if payload.get("type") == "Prompt":
            return "prompts"
        
        # 3. Policy (ODRL/OAC)
        context = str(payload.get("@context", ""))
        policy_types = ["Policy", "Agreement", "Offer", "Request", "Requirement"]
        if "odrl" in context.lower() or "oac" in context.lower() or payload.get("type") in policy_types:
            return "policy"
            
        # 4. Croissant
        if "recordSet" in payload or "@dataset" in payload or payload.get("dataset") == "Croissant":
            return "croissant"
            
        # 5. Organizations / Groups (Organization Ontology)
        org_types = ["Organization", "Membership", "Role", "FormalOrganization", "OrganizationalUnit", "OrganizationalCollaboration"]
        if payload.get("type") in org_types or "org:" in str(payload.get("@context", "")).lower():
            return "groups"
            
        # 6. Bookmarks
        if payload.get("@type") == "WebPage" or payload.get("type") == "WebPage" or "url" in payload:
            return "bookmarks"
            
        # Default
        return "dids"

    def _extract_text_content(self, payload: Dict[str, Any]) -> str:
        # Extract meaningful text from the payload for embedding
        parts = []
        if "name" in payload:
            parts.append(payload["name"])
        if "description" in payload:
            parts.append(payload["description"])
        if "type" in payload:
            parts.append(payload["type"])
        
        # Add nested unit info if present
        unit = payload.get("unit")
        if unit and isinstance(unit, dict):
            if "name" in unit:
                parts.append(f"unit: {unit['name']}")
            if "symbol" in unit:
                parts.append(f"symbol: {unit['symbol']}")
            if "description" in unit:
                parts.append(unit["description"])

        # Add title if present (generic DIDs)
        if "title" in payload:
            parts.append(payload["title"])

        if not parts:
            # Fallback to full JSON string if no specific fields found
            return json.dumps(payload)
        
        return " ".join(parts)

    def _did_to_id(self, did: str) -> str:
        import hashlib
        import uuid
        hash_val = hashlib.md5(did.encode()).hexdigest()
        return str(uuid.UUID(hash_val))

# Global instance
qdrant_service = QdrantService()
