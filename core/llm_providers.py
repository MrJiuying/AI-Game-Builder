from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json
import asyncio
import os
from openai import AsyncOpenAI


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_entity_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        scene_state: Optional[Dict[str, Any]] = None,
        history: list = None,
    ) -> str:
        pass

    @abstractmethod
    async def generate_text(self, system_prompt: str, user_text: str, history: list = None) -> str:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class DeepSeekProvider(BaseLLMProvider):
    def __init__(self, model: str = "deepseek-chat"):
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        self._api_key = api_key
        self._model = model
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url="https://api.deepseek.com/v1"
        )

    def get_provider_name(self) -> str:
        return "deepseek"

    def _build_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        scene_state: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if scene_state:
            messages.append(
                {
                    "role": "user",
                    "content": f"当前场景状态(JSON)：{json.dumps(scene_state, ensure_ascii=False)}",
                }
            )
        if history:
            for msg in history:
                messages.append(
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    }
                )
        messages.append({"role": "user", "content": user_prompt})
        return messages

    async def generate_text(self, system_prompt: str, user_text: str, history: list = None) -> str:
        messages = self._build_messages(
            system_prompt=system_prompt,
            user_prompt=user_text,
            history=history,
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return (response.choices[0].message.content or "").strip()

    async def generate_entity_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        scene_state: Optional[Dict[str, Any]] = None,
        history: list = None,
    ) -> str:
        messages = self._build_messages(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
            scene_state=scene_state,
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        return (response.choices[0].message.content or "").strip()


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

    async def generate_entity_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        scene_state: Optional[Dict[str, Any]] = None,
        history: list = None,
    ) -> str:
        
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

    async def generate_entity_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        scene_state: Optional[Dict[str, Any]] = None,
        history: list = None,
    ) -> str:
        
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
