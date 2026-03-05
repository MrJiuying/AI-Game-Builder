# AI-Game-Builder

> 版本: 0.0.2 | 将自然语言转化为 Godot 4.x 引擎的 2D 游戏实体

一个数据驱动的 AI 游戏装配平台，通过自然语言描述自动生成 Godot 4 游戏实体。

## 核心特性

- 🤖 **多模型支持**: DeepSeek、Claude、Ollama、GPT-4
- 🎮 **ECS 架构**: 遵循实体-组件系统，解耦设计
- 🔄 **实时装配**: WebSocket 实时广播，Godot 即时响应
- 🎨 **数据驱动**: Python 生成 JSON，Godot 读取装配

## 系统架构

```
用户输入 (自然语言)
       ↓
Vue 3 前端 → FastAPI 后端
       ↓
LLM Provider → 生成 JSON
       ↓
WebSocket 广播 → Godot LiveLink
       ↓
EntityAssembler 装配 → 游戏实体
```

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install fastapi uvicorn pydantic websockets

# 前端依赖
cd frontend
npm install
```

### 2. 启动后端

```bash
python server.py
# 服务运行在 http://localhost:8000
```

### 3. 启动前端

```bash
cd frontend
npm run dev
# 访问 http://localhost:5173
```

### 4. 启动 Godot

1. 打开 Godot 4.x
2. 导入 `godot_project` 目录
3. 创建新场景，挂载 `LiveLink.gd` 脚本
4. 运行场景

### 5. 使用流程

1. 在前端选择模型 (DeepSeek/Ollama/GPT-4)
2. 输入自然语言描述，如 "生成一个拿剑的刺客"
3. 点击发送
4. Godot 端自动接收并装配实体

## 项目结构

```
├── server.py                    # FastAPI + WebSocket 后端
├── core/                        # Python 核心模块
│   ├── models.py               # Pydantic 数据模型
│   ├── llm_providers.py        # LLM 提供者 (策略模式)
│   ├── agent_core.py           # 大模型调度器
│   └── project_manager.py       # 资源管理器
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── App.vue             # 主界面
│       └── components/         # UI 组件
│           ├── AIControlPanel.vue
│           ├── GameStage.vue
│           └── AssetPanel.vue
└── godot_project/             # Godot 4 项目
    ├── components/             # ECS 组件库
    │   ├── VelocityComponent.gd
    │   ├── HealthComponent.gd
    │   ├── HitboxComponent.gd
    └── HurtboxComponent.gd
    └── scripts/autoload/
        ├── EntityAssembler.gd  # 动态装配器
        ├── LiveLink.gd         # WebSocket 客户端
        └── AutoTestRunner.gd   # 自动测试
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/generate_entity` | POST | 生成游戏实体 |
| `/api/configs` | GET | 列出配置 |
| `/api/assets` | GET | 列出资源 |
| `/ws` | WebSocket | 实时广播 |

## 生成的 JSON 格式

```json
{
  "entity_name": "EnemySkeleton",
  "base_type": "CharacterBody2D",
  "components": ["VelocityComponent", "HealthComponent", "HitboxComponent"],
  "component_params": {
    "VelocityComponent": {"max_speed": 150.0, "acceleration": 800.0},
    "HealthComponent": {"max_health": 50.0},
    "HitboxComponent": {"damage": 10.0}
  },
  "sprite_path": "res://assets/sprites/enemy_skeleton.png"
}
```

## 技术栈

- **后端**: Python 3.10+, FastAPI, Pydantic, WebSocket
- **前端**: Vue 3, TypeScript, Tailwind CSS, Vite
- **游戏引擎**: Godot 4.x, GDScript
- **AI**: DeepSeek, OpenAI, Ollama

## 版本历史

### v0.0.2 (2026-03-05)
- 完善 Godot 4 WebSocket 通讯 (LiveLink.gd)
- 添加实体动态组件挂载能力
- 支持 AI 图像生成 (Local SD / DALL-E 3 / Cloud SD)
- 添加游戏基底 (genre) 上下文约束
- 添加动态能力组件库选择 UI
- 添加 Godot 一键启动功能 (编辑器模式)
- 添加本地 SD 代理绕过和超时优化
- 添加项目配置文件 (project.godot) 自动生成
- 修复多个 bug 并优化稳定性

### v0.0.1 (2026-03-04)
- 初始版本
- 多模型 LLM 支持
- Vue 3 前端 UI
- FastAPI + WebSocket 后端
- Godot 端实体装配器
- 完整的 AI → JSON → Godot 装配闭环

## 许可证

MIT License
