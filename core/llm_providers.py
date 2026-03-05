from abc import ABC, abstractmethod
from typing import Dict, Any
import json
import asyncio


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_entity_schema(self, prompt: str, history: list = None) -> str:
        pass

    @abstractmethod
    async def generate_text(self, system_prompt: str, user_text: str, history: list = None) -> str:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class DeepSeekProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self._api_key = api_key
        self._model = model

    def get_provider_name(self) -> str:
        return "deepseek"

    async def generate_text(self, system_prompt: str, user_text: str, history: list = None) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for msg in history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": user_text})
        
        await asyncio.sleep(0.1)
        return f"[DeepSeek mock] 已收到指令，将生成适当的回复。用户输入: {user_text}"

    async def generate_entity_schema(self, prompt: str, history: list = None) -> str:
        await asyncio.sleep(0.1)
        
        mock_response = {
            "entity_name": "EnemySkeleton",
            "base_type": "CharacterBody2D",
            "components": [
                {
                    "component_name": "VelocityComponent",
                    "parameters": {
                        "max_speed": 150.0,
                        "acceleration": 800.0,
                        "friction": 600.0
                    }
                },
                {
                    "component_name": "HealthComponent",
                    "parameters": {
                        "max_health": 50.0
                    }
                },
                {
                    "component_name": "HitboxComponent",
                    "parameters": {
                        "damage": 10.0
                    }
                }
            ],
            "sprite_path": "res://assets/sprites/enemy_skeleton.png",
            "metadata": {"ai_generated": True}
        }
        
        return json.dumps(mock_response, ensure_ascii=False)


class LocalOllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self._base_url = base_url
        self._model = model

    def get_provider_name(self) -> str:
        return "ollama"

    async def generate_text(self, system_prompt: str, user_text: str, history: list = None) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for msg in history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": user_text})
        
        await asyncio.sleep(0.1)
        return f"[Ollama mock] 已收到指令，将生成适当的回复。用户输入: {user_text}"

    async def generate_entity_schema(self, prompt: str, history: list = None) -> str:
        await asyncio.sleep(0.1)
        
        mock_response = {
            "entity_name": "PlayerWarrior",
            "base_type": "CharacterBody2D",
            "components": [
                {
                    "component_name": "VelocityComponent",
                    "parameters": {
                        "max_speed": 300.0,
                        "acceleration": 1000.0,
                        "friction": 800.0
                    }
                },
                {
                    "component_name": "HealthComponent",
                    "parameters": {
                        "max_health": 100.0
                    }
                },
                {
                    "component_name": "HurtboxComponent",
                    "parameters": {}
                }
            ],
            "sprite_path": "res://assets/sprites/player_warrior.png",
            "metadata": {"ai_generated": True, "model": self._model}
        }
        
        return json.dumps(mock_response, ensure_ascii=False)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self._api_key = api_key
        self._model = model

    def get_provider_name(self) -> str:
        return "openai"

    async def generate_text(self, system_prompt: str, user_text: str, history: list = None) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for msg in history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": user_text})
        
        await asyncio.sleep(0.1)
        return f"[OpenAI mock] 已收到指令，将生成适当的回复。用户输入: {user_text}"

    async def generate_entity_schema(self, prompt: str, history: list = None) -> str:
        await asyncio.sleep(0.1)
        
        mock_response = {
            "entity_name": "MagicOrb",
            "base_type": "Area2D",
            "components": [
                {
                    "component_name": "HitboxComponent",
                    "parameters": {
                        "damage": 25.0
                    }
                }
            ],
            "sprite_path": "res://assets/sprites/magic_orb.png",
            "metadata": {"ai_generated": True}
        }
        
        return json.dumps(mock_response, ensure_ascii=False)
