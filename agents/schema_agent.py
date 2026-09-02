import json
import os
from typing import Dict, Any

class SchemaAgent:
    """
    Responsible for providing relevant schema information to the Query Agent.
    Avoids dumping the entire schema into every prompt.
    """
    def __init__(self, manifest_path: str = "data/schema_manifest.json"):
        self.manifest_path = manifest_path
        self.schema_cache = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        with open(self.manifest_path, "r") as f:
            return json.load(f)

    def get_relevant_schema(self, question: str) -> str:
        """
        In a full implementation, this would use an LLM to pick only the 
        relevant tables. For Phase 2, it provides the manifest structure
        in a clean, optimized format.
        """
        # For Phase 2, we provide the structured manifest as a string.
        # Later, this will become a smart filter.
        return json.dumps(self.schema_cache, indent=2)

# Singleton instance
schema_agent = SchemaAgent()
