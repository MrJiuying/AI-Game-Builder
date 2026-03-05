from typing import Optional
import json
import logging

from core.llm_providers import BaseLLMProvider
from core.models import EntityConfig, ComponentConfig


logger = logging.getLogger(__name__)


# 游戏底座规则注册表
GENRE_PROMPTS = {
    "top_down_rpg": "当前项目为【俯视角 RPG】。实体在 2D 平面上自由移动，无重力。你必须配置的专属组件参数：TopDownMovementComponent (需提供 max_speed, acceleration, friction), CollisionGeneratorComponent (需提供 shape_type, radius, size_x, size_y)。",
    "platformer": "当前项目为【2D 横版跳跃】。实体受重力影响。可用专属核心组件：PlatformerMovementComponent (参数: speed, jump_force, gravity), PlatformerHitbox。",
    "top_down_shooter": "当前项目为【俯视角射击】。可用专属核心组件：AimingComponent, ProjectileEmitterComponent。"
}


class AgentCoordinator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self._llm_provider = llm_provider
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """你是一个游戏实体生成助手。请根据用户的描述生成符合以下 JSON Schema 的配置：

{
    "entity_name": "实体名称",
    "base_type": "CharacterBody2D | Area2D | StaticBody2D | Node2D",
    "components": [
        {
            "component_name": "组件名称",
            "parameters": { ... }
        }
    ],
    "sprite_path": "资源路径或null",
    "metadata": { ... }
}

通用组件：
- VelocityComponent: max_speed, acceleration, friction
- HealthComponent: max_health
- HitboxComponent: damage
- HurtboxComponent: (无参数)

请直接输出 JSON，不要包含任何解释或 markdown 标记。"""

    async def process_user_intent(self, user_text: str, game_base: Optional[str] = "top-down-rpg", required_components: Optional[list] = None) -> EntityConfig:
        # 获取游戏底座规则
        genre_prompt = GENRE_PROMPTS.get(game_base, "")
        
        # 构建完整的系统提示
        full_system_prompt = f"{self._system_prompt}\n\n{genre_prompt}\n\n你必须严格遵守当前底座的物理规则，且只能从上述可用组件中选择来组装 JSON。"
        
        # 添加必需组件到提示
        if required_components and len(required_components) > 0:
            components_text = ", ".join(required_components)
            user_text += f"\n\n用户已强制要求挂载以下组件：{components_text}。你在生成的 JSON components 列表中必须且只能包含这些组件，并在 component_params 中为它们分配合理的数值。"
        
        full_prompt = f"{full_system_prompt}\n\n用户需求：{user_text}"
        
        logger.info(f"正在调用 {self._llm_provider.get_provider_name()} 处理请求，游戏底座: {game_base}")
        
        json_string = await self._llm_provider.generate_entity_schema(full_prompt)
        
        raw_data = self._extract_json(json_string)
        
        entity_config = self._validate_and_parse(raw_data)
        
        logger.info(f"成功生成实体配置: {entity_config.entity_name}")
        
        return entity_config

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
