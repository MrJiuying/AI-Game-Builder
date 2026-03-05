from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import json
import asyncio
import uuid
import subprocess
import os
import sys
import socket
from pathlib import Path
from asyncio import Queue
from dotenv import load_dotenv

from core.agent_core import AgentCoordinator
from core.llm_providers import DeepSeekProvider, LocalOllamaProvider, OpenAIProvider
from core.project_manager import ProjectResourceManager
from core.image_providers import ProviderOfflineError
from core.image_router import ImageGeneratorCoordinator
from core.memory_manager import memory_manager

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Game Builder API",
    description="连接前端与大模型 + Godot 引擎的核心服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GODOT_PROJECT_PATH = Path(__file__).parent / "godot_project"
SPRITES_PATH = GODOT_PROJECT_PATH / "assets" / "sprites"
COMPONENTS_PATH = GODOT_PROJECT_PATH / "components"
STAGE_SAVE_PATH = Path(__file__).parent / "stage_save.json"

project_manager = ProjectResourceManager(str(GODOT_PROJECT_PATH))
image_coordinator = ImageGeneratorCoordinator()
app.mount("/static/sprites", StaticFiles(directory=str(SPRITES_PATH)), name="static_sprites")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 客户端连接，当前活跃连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket 客户端断开，当前活跃连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """向所有活跃客户端广播消息"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"发送广播失败: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
        
        logger.info(f"广播消息已发送给 {len(self.active_connections)} 个客户端: {message}")


manager = ConnectionManager()
stage_process: Optional[subprocess.Popen] = None


class GenerateEntityRequest(BaseModel):
    prompt: str
    mode: Optional[str] = "build"
    model_name: Optional[str] = "deepseek"
    api_key: Optional[str] = None
    image_provider: Optional[str] = "local_sd"
    lora_model: Optional[str] = None
    art_api_key: Optional[str] = None
    art_base_url: Optional[str] = None
    game_base: Optional[str] = "top-down-rpg"
    required_components: Optional[List[str]] = []
    direct_assembly: Optional[bool] = False
    entity_name: Optional[str] = None
    sprite_name: Optional[str] = None
    sprite_path: Optional[str] = None
    component_params: Optional[Dict[str, Dict[str, Any]]] = None


class TestImageProviderRequest(BaseModel):
    provider_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class LaunchGodotRequest(BaseModel):
    godot_path: Optional[str] = None


class ConfigRequest(BaseModel):
    deepseek_api_key: str


class SceneConfigRequest(BaseModel):
    background_image: Optional[str] = None
    background_color: Optional[str] = None
    physics_gravity: Optional[float] = None


class StageActivateRequest(BaseModel):
    godot_path: Optional[str] = None
    port: Optional[int] = 8060
    preset: Optional[str] = "Web"
    skip_export: Optional[bool] = False


class GodotPathConfigRequest(BaseModel):
    godot_path: str


class GenerateEntityResponse(BaseModel):
    status: str
    entity_name: Optional[str] = None
    config_path: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    text_reply: Optional[str] = None
    art_prompt: Optional[str] = None
    sprite_path: Optional[str] = None
    mode: Optional[str] = "build"


def get_llm_provider(model_name: str) -> AgentCoordinator:
    if model_name == "deepseek":
        provider = DeepSeekProvider()
    elif model_name == "ollama":
        provider = LocalOllamaProvider(model="llama3")
    elif model_name in ["gpt4", "openai"]:
        provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY", ""))
    else:
        provider = DeepSeekProvider()
    
    return AgentCoordinator(provider)


def _upsert_env_key(file_path: Path, key: str, value: str) -> None:
    lines: List[str] = []
    if file_path.exists():
        lines = file_path.read_text(encoding="utf-8").splitlines()

    updated_lines: List[str] = []
    replaced = False
    prefix = f"{key}="

    for line in lines:
        if line.startswith(prefix):
            updated_lines.append(f"{key}={value}")
            replaced = True
        else:
            updated_lines.append(line)

    if not replaced:
        updated_lines.append(f"{key}={value}")

    file_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def _default_global_config() -> Dict[str, Any]:
    return {
        "background_image": "",
        "background_color": "#0f172a",
        "physics_gravity": 980.0,
    }


def _normalize_stage_save(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {"entities": {}, "global_config": _default_global_config()}

    if "entities" in data or "global_config" in data:
        entities = data.get("entities", {})
        global_config = data.get("global_config", {})
        if not isinstance(entities, dict):
            entities = {}
        if not isinstance(global_config, dict):
            global_config = {}
        merged_config = _default_global_config()
        merged_config.update({k: v for k, v in global_config.items() if v is not None})
        return {"entities": entities, "global_config": merged_config}

    entities = {k: v for k, v in data.items() if isinstance(v, dict)}
    return {"entities": entities, "global_config": _default_global_config()}


def _load_stage_save() -> Dict[str, Any]:
    if not STAGE_SAVE_PATH.exists():
        return {"entities": {}, "global_config": _default_global_config()}
    try:
        data = json.loads(STAGE_SAVE_PATH.read_text(encoding="utf-8"))
        return _normalize_stage_save(data)
    except Exception:
        return {"entities": {}, "global_config": _default_global_config()}


def _write_stage_save(data: Dict[str, Any]) -> None:
    normalized = _normalize_stage_save(data)
    STAGE_SAVE_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def _upsert_saved_spawn(entity_data: Dict[str, Any]) -> None:
    entity_name = str(entity_data.get("entity_name", "")).strip()
    if not entity_name:
        return
    stage_data = _load_stage_save()
    entities = stage_data.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}
    entities[entity_name] = entity_data
    stage_data["entities"] = entities
    _write_stage_save(stage_data)


def _upsert_saved_update(action_data: Dict[str, Any]) -> None:
    entity_name = str(action_data.get("entity_name", "")).strip()
    component_name = str(action_data.get("component_name", "")).strip()
    parameters = action_data.get("parameters", {})
    if not entity_name or not component_name or not isinstance(parameters, dict):
        return

    stage_data = _load_stage_save()
    entities = stage_data.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}

    current = entities.get(entity_name, {})
    if not isinstance(current, dict):
        current = {}

    components = current.get("components", [])
    if not isinstance(components, list):
        components = []
    if component_name not in components:
        components.append(component_name)

    component_params = current.get("component_params", {})
    if not isinstance(component_params, dict):
        component_params = {}
    existing_params = component_params.get(component_name, {})
    if not isinstance(existing_params, dict):
        existing_params = {}
    existing_params.update(parameters)
    component_params[component_name] = existing_params

    current["entity_name"] = entity_name
    current["base_type"] = current.get("base_type", "CharacterBody2D")
    current["components"] = components
    current["component_params"] = component_params
    current["sprite_path"] = current.get("sprite_path", "")
    current["metadata"] = current.get("metadata", {})

    entities[entity_name] = current
    stage_data["entities"] = entities
    _write_stage_save(stage_data)


def _update_global_config(config_update: Dict[str, Any]) -> Dict[str, Any]:
    stage_data = _load_stage_save()
    current_config = stage_data.get("global_config", {})
    if not isinstance(current_config, dict):
        current_config = _default_global_config()
    merged = _default_global_config()
    merged.update(current_config)
    merged.update({k: v for k, v in config_update.items() if v is not None})
    stage_data["global_config"] = merged
    _write_stage_save(stage_data)
    return merged


async def _restore_stage_for_connection(websocket: WebSocket) -> None:
    stage_data = _load_stage_save()
    global_config = stage_data.get("global_config", {})
    if isinstance(global_config, dict):
        await websocket.send_json(
            {
                "action": "update_scene_config",
                "config": global_config,
            }
        )
    entities = stage_data.get("entities", {})
    if not isinstance(entities, dict):
        return
    for entity_name, entity_config in entities.items():
        if not isinstance(entity_config, dict):
            continue
        await websocket.send_json(
            {
                "action": "spawn_entity",
                "entity_name": entity_name,
                "entity_config": entity_config,
            }
        )


@app.get("/")
async def root():
    return {
        "service": "AI Game Builder API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "godot_project_path": str(GODOT_PROJECT_PATH),
        "websocket_connections": len(manager.active_connections)
    }


@app.get("/api/scene_state")
async def get_scene_state():
    state = getattr(memory_manager, "current_scene_state", None)
    if isinstance(state, dict):
        return state
    return {}


@app.post("/api/scene/config")
async def update_scene_config(request: SceneConfigRequest):
    config_update: Dict[str, Any] = {
        "background_image": request.background_image,
        "background_color": request.background_color,
        "physics_gravity": request.physics_gravity,
    }
    merged_config = _update_global_config(config_update)
    await manager.broadcast({"action": "update_scene_config", "config": merged_config})
    return {"status": "success", "global_config": merged_config}


@app.get("/api/assets/list")
async def list_assets_full():
    if not SPRITES_PATH.exists():
        sprites = []
    else:
        allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        sprites = [
            {
                "name": p.name,
                "url": f"/static/sprites/{p.name}",
            }
            for p in sorted(SPRITES_PATH.iterdir())
            if p.is_file() and p.suffix.lower() in allowed
        ]

    if not COMPONENTS_PATH.exists():
        components = []
    else:
        components = sorted([p.stem for p in COMPONENTS_PATH.glob("*.gd") if p.is_file()])

    return {"sprites": sprites, "components": components}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await _restore_stage_for_connection(websocket)

    async def listen_incoming() -> None:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"收到无效 JSON: {data}")
                continue

            action = message.get("action")
            if action == "ping":
                await websocket.send_json({"action": "pong"})
            elif action == "sync_state":
                state_data = message.get("data", {})
                if isinstance(state_data, dict):
                    memory_manager.update_scene_state(state_data)
                    logger.info("收到 sync_state，已写入 MemoryManager.current_scene_state")
                else:
                    logger.warning(f"sync_state.data 不是 dict: {state_data}")
            elif action == "engine_ready":
                stage_url = message.get("stage_url", "http://127.0.0.1:8060")
                await manager.broadcast(
                    {
                        "action": "engine_ready",
                        "stage_url": stage_url,
                        "source": message.get("source", "unknown"),
                    }
                )
                logger.info(f"收到 engine_ready 并已广播: {stage_url}")
            else:
                logger.info(f"收到未知 action: {action}")

    try:
        listener_task = asyncio.create_task(listen_incoming())
        await listener_task
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        manager.disconnect(websocket)


@app.post("/api/generate_entity", response_model=GenerateEntityResponse)
async def generate_entity(request: GenerateEntityRequest):
    mode = request.mode or "build"
    logger.info(f"收到生成请求: mode={mode}, model={request.model_name}, prompt={request.prompt[:50]}...")
    
    try:
        coordinator = get_llm_provider(request.model_name)
        
        # 保存用户消息到记忆
        memory_manager.add_message("user", request.prompt, mode)
        
        # ==================== CHAT 模式 ====================
        if mode == "chat":
            from core.agent_core import handle_chat_mode
            result = await handle_chat_mode(coordinator, request.prompt)
            text_reply = result["content"]
            memory_manager.add_message("assistant", text_reply, mode)
            
            return GenerateEntityResponse(
                status="success",
                message=text_reply,
                text_reply=text_reply,
                mode="chat"
            )
        
        # ==================== ART 模式 ====================
        elif mode == "art":
            from core.agent_core import handle_art_mode
            result = await handle_art_mode(coordinator, request.prompt)
            art_prompt = result["content"]
            
            try:
                art_api_key = request.art_api_key or request.api_key
                image_bytes = await image_coordinator.generate_image(
                    provider_name=request.image_provider,
                    prompt=art_prompt,
                    lora_model=request.lora_model,
                    api_key=art_api_key,
                    base_url=request.art_base_url
                )
                
                sprite_path = await project_manager.save_generated_asset(image_bytes, f"art_{uuid.uuid4().hex[:8]}")
                memory_manager.add_message("assistant", f"生成了美术资产，提示词: {art_prompt}", mode)
                
                return GenerateEntityResponse(
                    status="success",
                    message=f"🎨 美术资产生成成功！\n\n📝 提示词: {art_prompt}",
                    text_reply=art_prompt,
                    art_prompt=art_prompt,
                    sprite_path=sprite_path,
                    mode="art"
                )
            except ProviderOfflineError as e:
                logger.warning(f"图片提供者离线: {e}")
                return GenerateEntityResponse(
                    status="error",
                    message=f"❌ 图片生成失败: {e}",
                    error=str(e),
                    mode="art"
                )
        
        # ==================== BUILD 模式 (默认) ====================
        else:
            config_dir = GODOT_PROJECT_PATH / "configs"
            config_dir.mkdir(parents=True, exist_ok=True)

            async def persist_and_broadcast(entity_name: str, json_data: Dict[str, Any], success_message: str) -> GenerateEntityResponse:
                file_name = f"{entity_name}_{uuid.uuid4().hex[:8]}.json"
                config_path = config_dir / file_name
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                _upsert_saved_spawn(json_data)
                await manager.broadcast(
                    {
                        "action": "spawn_entity",
                        "config_path": str(config_path),
                        "entity_name": entity_name,
                    }
                )
                return GenerateEntityResponse(
                    status="success",
                    entity_name=entity_name,
                    config_path=str(config_path),
                    message=success_message,
                    mode="build"
                )

            if request.direct_assembly:
                raw_entity_name = (request.entity_name or "").strip()
                sprite_name = (request.sprite_name or "").strip()
                if not raw_entity_name and sprite_name:
                    raw_entity_name = Path(sprite_name).stem
                entity_name = raw_entity_name or f"VisualEntity_{uuid.uuid4().hex[:6]}"

                sprite_path = (request.sprite_path or "").strip()
                if not sprite_path and sprite_name:
                    sprite_path = f"res://assets/sprites/{sprite_name}"

                components = []
                for comp in request.required_components or []:
                    comp_name = str(comp).strip()
                    if comp_name and comp_name not in components:
                        components.append(comp_name)

                component_params: Dict[str, Dict[str, Any]] = {}
                if isinstance(request.component_params, dict):
                    for comp_name, comp_params in request.component_params.items():
                        if isinstance(comp_params, dict):
                            component_params[str(comp_name)] = comp_params
                for comp_name in components:
                    if comp_name not in component_params:
                        component_params[comp_name] = {}

                json_data = {
                    "entity_name": entity_name,
                    "base_type": "CharacterBody2D",
                    "components": components,
                    "component_params": component_params,
                    "sprite_path": sprite_path,
                    "metadata": {
                        "source": "visual_assembly",
                        "game_base": request.game_base or "",
                    },
                }
                memory_manager.add_message("assistant", f"视觉化组装实体 {entity_name} 完成", mode)
                return await persist_and_broadcast(entity_name, json_data, f"✅ 实体 [{entity_name}] 视觉化组装完成！")

            from core.agent_core import handle_build_mode
            result = await handle_build_mode(
                coordinator, 
                request.prompt, 
                request.game_base, 
                request.required_components
            )
            if result.get("type") == "action" and result.get("action") == "update_component":
                action_data = result.get("data", {})
                if not isinstance(action_data, dict):
                    raise ValueError("update_component data must be a dict")
                _upsert_saved_update(action_data)

                await manager.broadcast(action_data)

                return GenerateEntityResponse(
                    status="success",
                    entity_name=action_data.get("entity_name"),
                    message="⚡ 已下发组件增量更新指令",
                    mode="build",
                )

            entity_config = result["entity_config"]
            
            ai_response = f"生成了实体 {entity_config.entity_name}，包含组件: {[c.component_name for c in entity_config.components]}"
            memory_manager.add_message("assistant", ai_response, mode)
            
            # Leave empty by default; Godot side will use a safe fallback texture.
            entity_config.sprite_path = ""
            
            json_data = {
                "entity_name": entity_config.entity_name,
                "base_type": entity_config.base_type,
                "components": [c.component_name for c in entity_config.components],
                "component_params": {c.component_name: c.parameters for c in entity_config.components},
                "sprite_path": entity_config.sprite_path,
                "metadata": entity_config.metadata
            }
            return await persist_and_broadcast(entity_config.entity_name, json_data, f"✅ 实体 [{entity_config.entity_name}] 装配成功！")
        
    except ProviderOfflineError as e:
        logger.error(f"图片提供者离线: {e}")
        return GenerateEntityResponse(
            status="error",
            error=str(e),
            message="图片生成失败，请检查本地 SD WebUI 是否启动"
        )
    except Exception as e:
        logger.error(f"生成实体失败: {str(e)}")
        return GenerateEntityResponse(
            status="error",
            error=str(e),
            message="生成过程中出现错误"
        )


@app.post("/api/config")
async def save_config(request: ConfigRequest):
    deepseek_api_key = request.deepseek_api_key.strip()
    if not deepseek_api_key:
        raise HTTPException(status_code=400, detail="deepseek_api_key 不能为空")

    _upsert_env_key(ENV_PATH, "DEEPSEEK_API_KEY", deepseek_api_key)
    os.environ["DEEPSEEK_API_KEY"] = deepseek_api_key
    load_dotenv(dotenv_path=ENV_PATH, override=True)

    return {"status": "success", "message": "DeepSeek API Key 保存成功"}


@app.get("/api/chat/history")
async def get_chat_history(mode: str = "build"):
    history = memory_manager.get_history(mode)
    return {"status": "success", "history": history, "mode": mode}


@app.post("/api/chat/clear")
async def clear_chat_history(mode: Optional[str] = None):
    memory_manager.clear_history(mode)
    return {"status": "success", "message": "聊天历史已清空"}


@app.get("/api/configs")
async def list_configs():
    config_dir = GODOT_PROJECT_PATH / "configs"
    if not config_dir.exists():
        return {"configs": []}
    
    configs = []
    for f in config_dir.glob("*.json"):
        configs.append({
            "name": f.stem,
            "path": str(f),
            "modified": f.stat().st_mtime
        })
    
    return {"configs": configs}


@app.post("/api/save_sprite")
async def save_sprite(file_path: str, target_name: Optional[str] = None):
    try:
        godot_path = project_manager.save_sprite(file_path, target_name)
        return {"status": "success", "path": godot_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assets")
async def list_assets():
    try:
        sprites = project_manager.list_sprites()
        return {"sprites": sprites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate_image")
async def generate_image(
    prompt: str,
    provider: str = "local_sd",
    lora_model: Optional[str] = None,
    api_key: Optional[str] = None
):
    try:
        image_bytes = await image_coordinator.generate_image(
            provider_name=provider,
            prompt=prompt,
            lora_model=lora_model,
            api_key=api_key
        )
        
        # 保存临时图片
        temp_name = f"temp_{uuid.uuid4().hex[:8]}"
        sprite_path = await project_manager.save_generated_asset(image_bytes, temp_name)
        
        return {"status": "success", "path": sprite_path}
    except ProviderOfflineError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test_image_provider")
async def test_image_provider(request: TestImageProviderRequest):
    """测试图片提供者连接"""
    logger.info(f"收到测试请求: provider={request.provider_name}")
    
    try:
        # 构建提供者参数
        provider_kwargs = {}
        if request.api_key:
            provider_kwargs["api_key"] = request.api_key
        if request.base_url:
            provider_kwargs["base_url"] = request.base_url
        
        # 检查健康状态
        is_healthy = await image_coordinator.check_provider_health(
            provider_name=request.provider_name,
            **provider_kwargs
        )
        
        if is_healthy:
            return {"status": "success", "message": "连接成功"}
        else:
            return {"status": "error", "message": "连接失败，请检查服务状态"}
    except Exception as e:
        logger.error(f"测试图片提供者失败: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/launch_godot")
async def launch_godot(request: LaunchGodotRequest = None):
    """启动 Godot 引擎预览"""
    logger.info("收到启动 Godot 请求")
    
    # 如果没有指定 godot_path，为 None
    godot_path = request.godot_path if request else None
    
    # 如果前端没有传路径，返回错误提示
    if not godot_path:
        return {
            "status": "error",
            "message": "请先在系统设置中配置 Godot 引擎的可执行文件路径！"
        }
    
    try:
        # 设置预览场景
        setup_result = project_manager.setup_preview_stage()
        logger.info(f"预览场景设置完成: {setup_result}")
        
        # 获取 Godot 工程路径（使用 project_root 属性）
        project_path = str(project_manager.project_root)
        scene_path = setup_result["scene_godot_path"]
        
        # 构建 Godot 启动命令
        # 正确格式: godot --path <工程目录> -e (打开编辑器)
        cmd = [godot_path, "--path", project_path, "-e"]
        logger.info(f"启动命令: {' '.join(cmd)}")
        
        # 启动 Godot 进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_path
        )
        
        logger.info(f"Godot 进程已启动，PID: {process.pid}")
        
        return {
            "status": "success",
            "message": "Godot 引擎已启动",
            "pid": process.pid,
            "godot_path": godot_path,
            "project_path": project_path,
            "scene_path": scene_path
        }
    except FileNotFoundError:
        logger.error(f"找不到 Godot 可执行文件: {godot_path}")
        return {
            "status": "error",
            "message": f"指定的 Godot 路径无效: {godot_path}。请检查设置中的路径是否正确。"
        }
    except Exception as e:
        logger.error(f"启动 Godot 失败: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/system/godot_path")
async def get_godot_path():
    path = os.getenv("GODOT_PATH", "").strip()
    return {"status": "success", "godot_path": path}


@app.post("/api/system/godot_path")
async def set_godot_path(request: GodotPathConfigRequest):
    godot_path = request.godot_path.strip()
    if not godot_path:
        raise HTTPException(status_code=400, detail="godot_path 不能为空")
    _upsert_env_key(ENV_PATH, "GODOT_PATH", godot_path)
    os.environ["GODOT_PATH"] = godot_path
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    return {"status": "success", "message": "GODOT_PATH 已保存", "godot_path": godot_path}


@app.get("/api/stage/status")
async def stage_status():
    running = stage_process is not None and stage_process.poll() is None
    return {
        "status": "success",
        "running": running,
        "pid": stage_process.pid if running and stage_process is not None else None
    }


def _is_port_listening(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


@app.get("/api/stage/precheck")
async def stage_precheck(port: int = 8060, preset: str = "Web"):
    env_godot_path = os.getenv("GODOT_PATH", "").strip()
    path_ok = bool(env_godot_path) and Path(env_godot_path).exists()
    preset_file = Path(__file__).parent / "godot_project" / "export_presets.cfg"
    preset_file_ok = preset_file.exists()
    preset_name_ok = False
    if preset_file_ok:
        content = preset_file.read_text(encoding="utf-8", errors="ignore")
        preset_name_ok = f'name="{preset}"' in content
    return {
        "status": "success",
        "checks": {
            "godot_path_ok": path_ok,
            "export_preset_ok": preset_file_ok and preset_name_ok,
            "port_listening_ok": _is_port_listening("127.0.0.1", port),
        },
        "meta": {
            "godot_path": env_godot_path,
            "preset": preset,
            "port": port,
            "export_preset_file_exists": preset_file_ok,
            "export_preset_name_exists": preset_name_ok,
        }
    }


@app.post("/api/stage/activate")
async def activate_stage(request: StageActivateRequest):
    global stage_process
    running = stage_process is not None and stage_process.poll() is None
    if running:
        return {
            "status": "success",
            "message": "舞台服务已在运行",
            "pid": stage_process.pid
        }

    run_stage_path = Path(__file__).parent / "run_stage.py"
    if not run_stage_path.exists():
        raise HTTPException(status_code=500, detail=f"未找到脚本: {run_stage_path}")

    env_godot_path = os.getenv("GODOT_PATH", "").strip()
    godot_path = (request.godot_path or "").strip() or env_godot_path
    if not request.skip_export:
        if not godot_path:
            raise HTTPException(
                status_code=400,
                detail="未配置 GODOT_PATH。请在系统设置填写 Godot.exe 路径，或在环境变量中设置 GODOT_PATH。"
            )
        if not Path(godot_path).exists():
            raise HTTPException(
                status_code=400,
                detail=f"GODOT_PATH 无效: {godot_path}"
            )
        preset_file = Path(__file__).parent / "godot_project" / "export_presets.cfg"
        if not preset_file.exists():
            raise HTTPException(
                status_code=400,
                detail="缺少 godot_project/export_presets.cfg，请先在 Godot 配置 HTML5 导出预设。"
            )

    cmd = [
        sys.executable,
        str(run_stage_path),
        "--port",
        str(request.port or 8060),
        "--preset",
        request.preset or "Web",
    ]
    if request.skip_export:
        cmd.append("--skip-export")
    if godot_path:
        cmd.extend(["--godot-path", godot_path])
        _upsert_env_key(ENV_PATH, "GODOT_PATH", godot_path)
        os.environ["GODOT_PATH"] = godot_path
        load_dotenv(dotenv_path=ENV_PATH, override=True)

    try:
        stage_process = subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        await asyncio.sleep(1.0)
        if stage_process.poll() is not None:
            stderr_text = stage_process.stderr.read() if stage_process.stderr else ""
            stdout_text = stage_process.stdout.read() if stage_process.stdout else ""
            stage_process = None
            raise HTTPException(
                status_code=500,
                detail=f"run_stage.py 启动后立即退出。\nstdout: {stdout_text}\nstderr: {stderr_text}"
            )
        return {
            "status": "success",
            "message": "Godot Web Activator 已启动",
            "pid": stage_process.pid,
            "port": request.port or 8060
        }
    except Exception as e:
        logger.error(f"启动 run_stage.py 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/select_file")
async def select_file():
    """调用操作系统原生文件选择对话框"""
    import tkinter as tk
    from tkinter import filedialog
    
    try:
        # 创建隐藏的根窗口
        root = tk.Tk()
        root.withdraw()
        
        # 强制窗口置顶，防止被浏览器挡住
        root.attributes('-topmost', True)
        
        # 弹出文件选择框，仅限 .exe 文件
        file_path = filedialog.askopenfilename(
            title="请选择 Godot 引擎可执行文件",
            filetypes=[("Godot Executable", "*.exe"), ("All Files", "*.*")]
        )
        
        root.destroy()
        
        if file_path:
            logger.info(f"用户选择的文件: {file_path}")
            return {"path": file_path}
        else:
            return {"path": ""}
    except Exception as e:
        logger.error(f"打开文件选择对话框失败: {e}")
        return {"path": "", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
