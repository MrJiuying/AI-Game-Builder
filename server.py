from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import json
import uuid
import subprocess
import os
from pathlib import Path
from asyncio import Queue

from core.agent_core import AgentCoordinator
from core.llm_providers import DeepSeekProvider, LocalOllamaProvider, OpenAIProvider
from core.project_manager import ProjectResourceManager
from core.image_providers import ProviderOfflineError
from core.image_router import ImageGeneratorCoordinator
from core.memory_manager import memory_manager

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

project_manager = ProjectResourceManager(str(GODOT_PROJECT_PATH))
image_coordinator = ImageGeneratorCoordinator()


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


class GenerateEntityRequest(BaseModel):
    prompt: str
    model_name: Optional[str] = "deepseek"
    api_key: Optional[str] = None
    image_provider: Optional[str] = "local_sd"
    lora_model: Optional[str] = None
    art_api_key: Optional[str] = None
    art_base_url: Optional[str] = None
    game_base: Optional[str] = "top-down-rpg"
    required_components: Optional[List[str]] = []


class TestImageProviderRequest(BaseModel):
    provider_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class LaunchGodotRequest(BaseModel):
    godot_path: Optional[str] = None


class GenerateEntityResponse(BaseModel):
    status: str
    entity_name: Optional[str] = None
    config_path: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


def get_llm_provider(model_name: str, api_key: Optional[str] = None) -> AgentCoordinator:
    if model_name == "deepseek":
        provider = DeepSeekProvider(api_key=api_key or "sk-mock-key")
    elif model_name == "ollama":
        provider = LocalOllamaProvider(model="llama3")
    elif model_name in ["gpt4", "openai"]:
        provider = OpenAIProvider(api_key=api_key or "sk-mock-key")
    else:
        provider = DeepSeekProvider(api_key=api_key or "sk-mock-key")
    
    return AgentCoordinator(provider)


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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.info(f"收到 WebSocket 消息: {message}")
                
                if message.get("action") == "ping":
                    await websocket.send_json({"action": "pong"})
            except json.JSONDecodeError:
                logger.warning(f"收到无效 JSON: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        manager.disconnect(websocket)


@app.post("/api/generate_entity", response_model=GenerateEntityResponse)
async def generate_entity(request: GenerateEntityRequest):
    logger.info(f"收到生成请求: model={request.model_name}, image_provider={request.image_provider}, prompt={request.prompt[:50]}...")
    
    try:
        coordinator = get_llm_provider(request.model_name, request.api_key)
        
        # 保存用户消息到记忆
        memory_manager.add_message("user", request.prompt)
        
        # 1. 调用 LLM 获取游戏配置和美术提示词
        entity_config = await coordinator.process_user_intent(
            request.prompt, 
            game_base=request.game_base,
            required_components=request.required_components
        )
        
        # 保存 AI 响应到记忆
        ai_response = f"生成了实体 {entity_config.entity_name}，包含组件: {[c.component_name for c in entity_config.components]}"
        memory_manager.add_message("assistant", ai_response)
        
        # 2. 生成美术提示词（这里简化处理，实际应该从 LLM 输出中提取）
        art_prompt = f"生成一个 {entity_config.entity_name} 的 2D 游戏角色，清晰、风格化，适合俯视角游戏"
        
        # 3. 生成图片
        try:
            # 对于云端图片提供者，使用美术专用 API Key
            art_api_key = request.art_api_key or request.api_key
            image_bytes = await image_coordinator.generate_image(
                provider_name=request.image_provider,
                prompt=art_prompt,
                lora_model=request.lora_model,
                api_key=art_api_key,
                base_url=request.art_base_url
            )
            
            # 4. 保存图片
            sprite_path = await project_manager.save_generated_asset(image_bytes, entity_config.entity_name)
            entity_config.sprite_path = sprite_path
        except ProviderOfflineError as e:
            logger.warning(f"图片提供者离线: {e}")
            # 继续流程，使用默认图片
            entity_config.sprite_path = "res://icon.svg"
        
        # 5. 保存 JSON 配置
        config_dir = GODOT_PROJECT_PATH / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = f"{entity_config.entity_name}_{uuid.uuid4().hex[:8]}.json"
        config_path = config_dir / file_name
        
        json_data = {
            "entity_name": entity_config.entity_name,
            "base_type": entity_config.base_type,
            "components": [c.component_name for c in entity_config.components],
            "component_params": {c.component_name: c.parameters for c in entity_config.components},
            "sprite_path": entity_config.sprite_path,
            "metadata": entity_config.metadata
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"实体配置已保存: {config_path}")
        
        # 6. 广播给 Godot
        broadcast_message = {
            "action": "spawn_entity",
            "config_path": str(config_path),
            "entity_name": entity_config.entity_name
        }
        await manager.broadcast(broadcast_message)
        
        return GenerateEntityResponse(
            status="success",
            entity_name=entity_config.entity_name,
            config_path=str(config_path),
            message=f"成功生成实体 {entity_config.entity_name}"
        )
        
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


@app.get("/api/chat/history")
async def get_chat_history():
    history = memory_manager.get_history()
    return {"status": "success", "history": history}


@app.post("/api/chat/clear")
async def clear_chat_history():
    memory_manager.clear_history()
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
