from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ComponentConfig(BaseModel):
    component_name: str = Field(description="组件名称，如 VelocityComponent, HealthComponent")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="组件参数字典")


class EntityConfig(BaseModel):
    entity_name: str = Field(description="实体名称")
    base_type: str = Field(description="基础类型，如 CharacterBody2D, Area2D, StaticBody2D")
    components: List[ComponentConfig] = Field(default_factory=list, description="组件配置列表")
    sprite_path: Optional[str] = Field(default=None, description="外部美术资源路径")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class GameSceneConfig(BaseModel):
    scene_name: str = Field(description="场景名称")
    entities: List[EntityConfig] = Field(default_factory=list, description="场景中的实体列表")
