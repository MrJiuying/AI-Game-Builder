from __future__ import annotations
from typing import Optional, List, Dict
import json
import logging

from core.llm_providers import BaseLLMProvider
from core.models import EntityConfig, ComponentConfig
from core.memory_manager import memory_manager


logger = logging.getLogger(__name__)

def _format_scene_state_for_prompt() -> str:
    state = getattr(memory_manager, "current_scene_state", None)
    if not state:
        return ""
    try:
        payload = json.dumps(state, ensure_ascii=False)
    except TypeError:
        payload = str(state)
    return f"\n\n【当前 Godot 引擎实时状态反馈】：{payload}\n"


# 游戏底座规则注册表
GENRE_PROMPTS = {
    "top_down_rpg": "当前项目为【俯视角 RPG】。实体在 2D 平面上自由移动，无重力。你必须配置的专属组件参数：TopDownMovementComponent (需提供 max_speed, acceleration, friction), CollisionGeneratorComponent (需提供 shape_type, radius, size_x, size_y)。",
    "platformer": "当前项目为【2D 横版跳跃】。实体受重力影响。可用专属核心组件：PlatformerMovementComponent (参数: speed, jump_force, gravity), PlatformerHitbox。",
    "top_down_shooter": "当前项目为【俯视角射击】。可用专属核心组件：AimingComponent, ProjectileEmitterComponent。"
}

# 系统提示词
SYSTEM_PROMPTS = {
    "chat": """你现在是纯文本聊天模式。

你是一个资深游戏策划和编剧。你的任务是与用户探讨游戏设定、剧情、角色背景或数值平衡。

严禁输出任何 JSON、代码块或参数字典。请使用生动的自然语言进行对话。
禁止使用任何 Markdown 代码块（如 ```）包裹内容。
如果你在对话中引用之前的实体，请使用纯文字描述（例如'那个速度为150的骷髅'），严禁复现 JSON 结构。
如果你看到历史记录里有 JSON，请完全忽略它们的格式，只关注其中的创意内容。""",
    
    "build": """你是一个严谨的游戏数据工程师。你只能输出符合 Godot 规范的纯 JSON 字典。

严禁输出任何解释性文字或自然语言。你必须严格遵守当前底座的物理规则，且只能从可用组件中选择来组装 JSON。

通用组件：
- VelocityComponent: max_speed, acceleration, friction
- HealthComponent: max_health
- HitboxComponent: damage
- HurtboxComponent: (无参数)

新能力（增量修改 / Function Calling）：
如果你判断用户的需求是【修改场上现有实体的属性】而不是生成新实体，请输出以下动作格式（只输出 JSON）：
{"action": "update_component", "entity_name": "实体名", "component_name": "组件名", "parameters": {"参数名": 新数值}}

请直接输出 JSON，不要包含任何解释或 markdown 标记。""",
    
    "art": """你是一个英文 Stable Diffusion 提示词生成器。你的任务是把用户的中文描述转换成高质量的英文图像生成提示词。

规则：
1. 只输出英文提示词
2. 不要输出任何中文、中文标点、JSON 或代码块
3. 不要添加任何解释、闲聊或自我介绍

示例：
用户：生成一个红色的战士角色
输出：red warrior character, 2D game sprite, top-down view, pixel art style, detailed, game asset

用户：可爱的蓝色史莱姆
输出：cute blue slime creature, 2D game sprite, cartoon style, cute, round shape, game asset

用户：黑暗骑士装备
输出：dark knight armor, 2D game sprite, metallic armor, dark fantasy, detailed, game asset

现在请根据用户的描述生成英文提示词：
"""
}


# ============ 独立函数：聊天模式 ============
async def handle_chat_mode(llm_provider: AgentCoordinator, user_text: str) -> Dict:
    """💡 创意助理模式 - 纯文本对话"""
    provider_name = llm_provider._llm_provider.get_provider_name()
    logger.info(f"【Chat模式】正在调用 {provider_name} 处理闲聊请求")
    
    history = memory_manager.get_messages_for_llm("chat")

    scene_state_prompt = _format_scene_state_for_prompt()
    if scene_state_prompt:
        user_text = f"{scene_state_prompt}\n用户输入：{user_text}"
    
    response = await llm_provider._llm_provider.generate_text(
        system_prompt=SYSTEM_PROMPTS['chat'],
        user_text=user_text,
        history=history
    )
    
    logger.info(f"【Chat模式】成功获取文本回复")
    
    return {
        "type": "text",
        "content": response
    }


# ============ 独立函数：构建模式 ============
def _build_build_system_prompt(game_base: str, required_components: list = None) -> str:
    genre_prompt = GENRE_PROMPTS.get(game_base, "")
    system_prompt = SYSTEM_PROMPTS["build"]
    
    full_prompt = f"{system_prompt}\n\n{genre_prompt}"
    
    if required_components and len(required_components) > 0:
        components_text = ", ".join(required_components)
        full_prompt += f"\n\n用户已强制要求挂载以下组件：{components_text}。"
    
    return full_prompt


def _extract_json(raw_string: str) -> dict:
    cleaned = raw_string.strip()
    
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    
    cleaned = cleaned.strip()
    
    return json.loads(cleaned)


def _validate_and_parse(data: dict) -> EntityConfig:
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


async def handle_build_mode(llm_provider: AgentCoordinator, user_text: str, 
                           game_base: str = "top-down-rpg", 
                           required_components: list = None) -> Dict:
    """🛠️ 实体工坊模式 - JSON 实体生成"""
    provider_name = llm_provider._llm_provider.get_provider_name()
    logger.info(f"【Build模式】正在调用 {provider_name} 处理实体生成请求")
    
    system_prompt = _build_build_system_prompt(game_base, required_components)
    scene_state = getattr(memory_manager, "current_scene_state", None)
    history = memory_manager.get_messages_for_llm("build")
    
    json_string = await llm_provider._llm_provider.generate_entity_schema(
        system_prompt=system_prompt,
        user_prompt=f"用户需求：{user_text}",
        scene_state=scene_state if isinstance(scene_state, dict) else None,
        history=history
    )
    
    raw_data = _extract_json(json_string)

    # 增量修改动作：原样透传给上层（server -> websocket -> Godot）
    if isinstance(raw_data, dict) and raw_data.get("action") == "update_component":
        logger.info(
            "【Build模式】识别到增量修改动作: entity=%s component=%s",
            raw_data.get("entity_name"),
            raw_data.get("component_name"),
        )
        return {
            "type": "action",
            "action": "update_component",
            "data": raw_data,
        }

    entity_config = _validate_and_parse(raw_data)

    logger.info(f"【Build模式】成功生成实体配置: {entity_config.entity_name}")

    return {
        "type": "entity",
        "entity_config": entity_config
    }


# ============ 独立函数：美术模式 ============
async def handle_art_mode(llm_provider: AgentCoordinator, user_text: str) -> Dict:
    """🎨 美术中心模式 - SD Prompt 生成"""
    provider_name = llm_provider._llm_provider.get_provider_name()
    logger.info(f"【Art模式】正在调用 {provider_name} 处理美术提示词")
    
    response = await llm_provider._llm_provider.generate_text(
        system_prompt=SYSTEM_PROMPTS['art'],
        user_text=f"用户需求：{user_text}",
        history=[]
    )
    
    logger.info(f"【Art模式】成功获取提示词: {response[:50]}...")
    
    return {
        "type": "art_prompt",
        "content": response
    }


# ============ AgentCoordinator 类（保留兼容性） ============
class AgentCoordinator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self._llm_provider = llm_provider

    async def process_request(self, mode: str, user_text: str, game_base: str = "top-down-rpg", 
                             required_components: list = None) -> Dict:
        """统一的请求处理入口，根据 mode 分发"""
        
        if mode == "chat":
            return await handle_chat_mode(self, user_text)
        elif mode == "build":
            return await handle_build_mode(self, user_text, game_base, required_components)
        elif mode == "art":
            return await handle_art_mode(self, user_text)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def switch_provider(self, new_provider: BaseLLMProvider) -> None:
        self._llm_provider = new_provider
        logger.info(f"已切换 LLM 提供者: {new_provider.get_provider_name()}")

    async def chat_mode(self, user_text: str) -> str:
        """Legacy method for compatibility"""
        result = await handle_chat_mode(self, user_text)
        return result["content"]

    async def art_mode(self, user_text: str) -> str:
        """Legacy method for compatibility"""
        result = await handle_art_mode(self, user_text)
        return result["content"]
