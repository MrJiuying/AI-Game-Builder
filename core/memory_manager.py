import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, storage_path: str = "godot_project/configs/chat_history.json"):
        self.storage_path = Path(storage_path)
        self._ensure_storage_file()
    
    def _ensure_storage_file(self):
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_history([])
    
    def _load_history(self) -> List[Dict]:
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_history(self, history: List[Dict]):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存聊天历史失败: {e}")
    
    def get_history(self) -> List[Dict]:
        return self._load_history()
    
    def add_message(self, role: str, content: str):
        history = self._load_history()
        history.append({
            "role": role,
            "content": content
        })
        self._save_history(history)
        logger.info(f"已添加消息: role={role}, content长度={len(content)}")
    
    def clear_history(self):
        self._save_history([])
        logger.info("聊天历史已清空")
    
    def get_messages_for_llm(self) -> List[Dict]:
        history = self._load_history()
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]


memory_manager = MemoryManager()
