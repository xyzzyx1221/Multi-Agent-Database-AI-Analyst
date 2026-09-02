import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class ConversationStore:
    """
    Simple file-based conversation store to persist history.
    In production, this would be a Postgres table or Redis.
    """
    def __init__(self, storage_dir: str = "logs/traces"):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    def _get_file_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"session_{session_id}.json")

    def save_turn(self, session_id: str, turn_data: Dict[str, Any]):
        path = self._get_file_path(session_id)
        history = self.load_history(session_id)
        history.append(turn_data)
        
        with open(path, "w") as f:
            json.dump(history, f, indent=2)

    def load_history(self, session_id: str) -> List[Dict[str, Any]]:
        path = self._get_file_path(session_id)
        if not os.path.exists(path):
            return []
        
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def clear_history(self, session_id: str):
        path = self._get_file_path(session_id)
        if os.path.exists(path):
            os.remove(path)

# Singleton instance
conversation_store = ConversationStore()
