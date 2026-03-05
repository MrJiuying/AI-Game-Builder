import re
from typing import Optional, List, Dict
import json
import logging

from core.llm_providers import BaseLLMProvider
from core.models import EntityConfig, ComponentConfig
from core.memory_manager import memory_manager


logger = logging.getLogger(__name__)


# 游戏底座规则注册表
GENRE_PROMPTS = {
    "top_down_rpg": "当前项目为【俯视角 RPG】。实体在 2D 平面上自由移动，无重力。你必须配置的专属组件参数：TopDownMovementComponent (需提供 max_speed, acceleration, friction), CollisionGeneratorComponent (需提供 shape_type, radius, size_x, size_y)。",
    "platformer": "当前项目为【2D 横版跳跃】。实体受重力影响。可用专属核心组件：PlatformerMovementComponent (参数: speed, jump_force, gravity), PlatformerHitbox。",
    "top_down_shooter": "当前项目为【俯视角射击】。可用专属核心组件：AimingComponent, ProjectileEmitterComponent。"
}

# 系统提示词
SYSTEM_PROMPTS = {
    "chat": """你是一个资深游戏策划和编剧。你的任务是与用户探讨游戏设定、剧情、角色背景或数值平衡。

严禁输出任何 JSON、代码块或参数字典。请使用生动的自然语言进行对话。

如果你看到历史记录里有 JSON，请完全忽略它们的格式，只关注其中的创意内容。""",
    
    "build": """你是一个严谨的游戏数据工程师。你只能输出符合 Godot 规范的纯 JSON 字典。

严禁输出任何解释性文字或自然语言。你必须严格遵守当前底座的物理规则，且只能从可用组件中选择来组装 JSON。

通用组件：
- VelocityComponent: max_speed, acceleration, friction
- HealthComponent: max_health
- HitboxComponent: damage
- HurtboxComponent: (无参数)

请直接输出 JSON，不要包含任何解释或 markdown 标记。""",
    
    "art": """你是一个 AI 绘画提示词专家。请将用户描述转化为英文的 Stable Diffusion Prompt。

只输出 Prompt 文本，不要有任何中文解释。不要输出 JSON 或任何代码块。"""
}


def filter_history_for_chat(history: List[Dict]) -> List[Dict]:
    """过滤历史记录中的 JSON，替换为简洁描述"""
    json_pattern = re.compile(r'\{[^{}]*"entity_name"[^{}]*\}', re.DOTALL)
    
    filtered = []
    for msg in history:
        content = msg.get("content", "")
        if json_pattern.search(content):
            content = "[之前生成的实体配置数据]"
        filtered.append({"role": msg.get("role"), "content": content})
    return filtered


class AgentCoordinator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self._llm_provider = llm_provider

    def _build_build_system_prompt(self, game_base: str, required_components: list = None) -> str:
        genre_prompt = GENRE_PROMPTS.get(game_base, "")
        system_prompt = SYSTEM_PROMPTS["build"]
        
        full_prompt = f"{system_prompt}\n\n{genre_prompt}"
        
        if required_components and len(required_components) > 0:
            components_text = ", ".join(required_components)
            full_prompt += f"\n\n用户已强制要求挂载以下组件：{components_text}。"
        
        return full_prompt

    async def process_request(self, mode: str, user_text: str, game_base: str = "top-down-rpg", 
                             required_components: list = None) -> Dict:
        """统一的请求处理入口，根据 mode 分发"""
        
        if mode == "chat":
            return await self._process_chat(user_text)
        elif mode == "build":
            return await self._process_build(user_text, game_base, required_components)
        elif mode == "art":
            return await self._process_art(user_text)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    async def _process_chat(self, user_text: str) -> Dict:
        """💡 创意助理模式 - 纯文本对话"""
        logger.info(f"【Chat模式】正在调用 {self._llm_provider.get_provider_name()} 处理闲聊请求")
        
        history = memory_manager.get_messages_for_llm("chat")
        filtered_history = filter_history_for_chat(history)
        
        full_prompt = f"{SYSTEM_PROMPTS['chat']}\n\n用户：{user_text}"
        
        response = await self._llm_provider.generate_entity_schema(full_prompt, filtered_history)
        
        logger.info(f"【Chat模式】成功获取文本回复")
        
        return {
            "type": "text",
            "content": response
        }

    async def _process_build(self, user_text: str, game_base: str, required_components: list = None) -> Dict:
        """🛠️ 实体工坊模式 - JSON 实体生成"""
        logger.info(f"【Build模式】正在调用 {self._llm_provider.get_provider_name()} 处理实体生成请求")
        
        system_prompt = self._build_build_system_prompt(game_base, required_components)
        full_prompt = f"{system_prompt}\n\n用户需求：{user_text}"
        
        history = memory_manager.get_messages_for_llm("build")
        
        json_string = await self._llm_provider.generate_entity_schema(full_prompt, history)
        
        raw_data = self._extract_json(json_string)
        
        entity_config = self._validate_and_parse(raw_data)
        
        logger.info(f"【Build模式】成功生成实体配置: {entity_config.entity_name}")
        
        return {
            "type": "entity",
            "entity_config": entity_config
        }

    async def _process_art(self, user_text: str) -> Dict:
        """🎨 美术中心模式 - SD Prompt 生成"""
        logger.info(f"【Art模式】正在调用 {self._llm_provider.get_provider_name()} 处理美术提示词")
        
        full_prompt = f"{SYSTEM_PROMPTS['art']}\n\n用户需求：{user_text}"
        
        response = await self._llm_provider.generate_entity_schema(full_prompt)
        
        logger.info(f"【Art模式】成功获取提示词: {response[:50]}...")
        
        return {
            "type": "art_prompt",
            "content": response
        }

    def _extract_json(self, raw_string: str) -> dict:
        cleaned = raw_string.strip()
        
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        return json.loads(cleaned)

    def _validate_and_parse(self, data: dict) -> EntityConfig:
        entity_name = data.get("entity_name", "UnnamedEntity")
        base_type = data.get("base_type", "Node2D")
        
        components = []
        for comp_data in data.get("components", []):
            comp_name = comp_data.get("component_name", "")
            comp_params = comp_data.get("parameters", {})
            
            components.append(ComponentConfig(
                component_name=comp_name,
                parameters=comp_params
            ))
        
        return EntityConfig(
            entity_name=entity_name,
            base_type=base_type,
            components=components,
            sprite_path=data.get("sprite_path"),
            metadata=data.get("metadata", {})
        )

    def switch_provider(self, new_provider: BaseLLMProvider) -> None:
        self._llm_provider = new_provider
        logger.info(f"已切换 LLM 提供者: {new_provider.get_provider_name()}")

    async def chat_mode(self, user_text: str) -> str:
        """Legacy method for compatibility"""
        result = await self._process_chat(user_text)
        return result["content"]

    async def art_mode(self, user_text: str) -> str:
        """Legacy method for compatibility"""
        result = await self._process_art(user_text)
        return result["content"]
