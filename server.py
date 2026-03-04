from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import json
import uuid
from pathlib import Path
from asyncio import Queue

from core.agent_core import AgentCoordinator
from core.llm_providers import DeepSeekProvider, LocalOllamaProvider, OpenAIProvider
from core.project_manager import ProjectResourceManager

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
    logger.info(f"收到生成请求: model={request.model_name}, prompt={request.prompt[:50]}...")
    
    try:
        coordinator = get_llm_provider(request.model_name, request.api_key)
        
        entity_config = await coordinator.process_user_intent(request.prompt)
        
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
        
    except Exception as e:
        logger.error(f"生成实体失败: {str(e)}")
        return GenerateEntityResponse(
            status="error",
            error=str(e),
            message="生成过程中出现错误"
        )


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
