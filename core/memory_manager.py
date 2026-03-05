import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, storage_dir: str = "godot_project/configs"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_storage_path(self, mode: str = "build") -> Path:
        return self.storage_dir / f"chat_history_{mode}.json"
    
    def _load_history(self, mode: str = "build") -> List[Dict]:
        storage_path = self._get_storage_path(mode)
        try:
            if storage_path.exists():
                with open(storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return []
    
    def _save_history(self, history: List[Dict], mode: str = "build"):
        storage_path = self._get_storage_path(mode)
        try:
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存聊天历史失败: {e}")
    
    def get_history(self, mode: str = "build") -> List[Dict]:
        return self._load_history(mode)
    
    def add_message(self, role: str, content: str, mode: str = "build"):
        history = self._load_history(mode)
        history.append({
            "role": role,
            "content": content,
            "mode": mode
        })
        self._save_history(history, mode)
        logger.info(f"已添加消息: mode={mode}, role={role}, content长度={len(content)}")
    
    def clear_history(self, mode: Optional[str] = None):
        if mode:
            self._save_history([], mode)
            logger.info(f"聊天历史已清空: mode={mode}")
        else:
            for m in ["chat", "build", "art"]:
                self._save_history([], m)
            logger.info("所有聊天历史已清空")
    
    def get_messages_for_llm(self, mode: str = "build") -> List[Dict]:
        history = self._load_history(mode)
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]


memory_manager = MemoryManager()
