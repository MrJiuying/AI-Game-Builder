# AI-Game-Builder

> 版本: 0.0.3 | AI 驱动的 Godot 4 游戏装配与可视化控制台

一个面向 Godot 4.x 的全栈 AI 游戏控制台：支持自然语言生成/修改实体、实时同步场景状态、场景断线恢复、以及前端可视化资源浏览。

## 核心能力

- 🤖 多模型 AI 驱动（DeepSeek / GPT / Ollama）
- 🛠️ 三模式工作流（创意聊天、实体构建、美术生成）
- 🔄 WebSocket 实时联动（后端广播 + Godot 热更新）
- 🧠 场景状态闭环（Godot 上报 → 后端记忆 → AI 读取）
- 💾 场景持久化恢复（stage_save.json 自动存档与重连恢复）
- 🖼️ 前端资源库（贴图网格 + 组件芯片可视化）

## 系统架构

```text
用户输入（前端 Vue）
  ↓
FastAPI（路由、LLM 调度、WebSocket 中枢）
  ↓
LLM Provider（chat/build/art）
  ↓
JSON/Action 广播到 Godot（spawn_entity / update_component）
  ↓
Godot LiveLink 执行并回传 sync_state
  ↓
memory_manager.current_scene_state（供 AI 与前端读取）
```

## 主要功能说明

### 1) AI 构建与热更新
- `build` 模式生成实体配置 JSON，并广播 `spawn_entity`
- 增量修改时广播 `update_component`，Godot 对指定实体组件热更新
- 支持多实体同屏驻留，同名实体重建覆盖

### 2) 场景状态记忆与 Inspector
- Godot 定期发送 `sync_state` 到后端
- 后端写入 `memory_manager.current_scene_state`
- 前端每 1.5 秒拉取 `/api/scene_state`，在 Inspector 中实时展示实体与组件参数

### 3) 资源库（Asset Browser）
- 后端静态托管 `godot_project/assets/sprites` 到 `/static/sprites`
- 后端 `/api/assets/list` 返回：
  - `sprites`: `[{ name, url }]`
  - `components`: `["VelocityComponent", ...]`
- 前端展示：
  - 🎨 美术图库：图片缩略图网格
  - 🧩 能力芯片：组件标签列表

### 4) 场景持久化与自动恢复
- 服务维护 `stage_save.json`
- 每次下发 `spawn_entity` / `update_component` 前先更新存档
- Godot 连接 `/ws` 后，后端自动回放存档实体（`spawn_entity`）

### 5) 模型与配置
- DeepSeek Key 可通过前端保存到后端 `.env`
- 后端启动时自动加载 `.env`（`python-dotenv`）

## 快速开始

### 1. 安装依赖

```bash
# Python
pip install fastapi uvicorn pydantic websockets openai python-dotenv

# Frontend
cd frontend
npm install
```

### 2. 启动后端

```bash
python server.py
# http://localhost:8000
```

### 3. 启动前端

```bash
cd frontend
npm run dev
# 默认 http://localhost:1420
```

### 4. 启动 Godot 预览

- 打开 `godot_project`（Godot 4.x）
- 场景脚本入口为 `res://scripts/LiveLink.gd`
- 运行后会自动连接 `ws://127.0.0.1:8000/ws`

## API 速览

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/generate_entity` | POST | chat/build/art 统一入口 |
| `/api/scene_state` | GET | 获取实时场景状态 |
| `/api/assets/list` | GET | 获取贴图与组件列表 |
| `/static/sprites/{file}` | GET | 访问本地贴图静态资源 |
| `/api/config` | POST | 保存 DeepSeek API Key |
| `/api/chat/history` | GET | 获取聊天历史 |
| `/api/chat/clear` | POST | 清空聊天历史 |
| `/api/launch_godot` | POST | 启动 Godot 编辑器 |
| `/api/test_image_provider` | POST | 测试图像提供者连接 |
| `/ws` | WebSocket | Godot 实时通信通道 |

## WebSocket 动作协议

- 后端 → Godot
  - `spawn_entity`: 生成实体（支持 `config_path` 或 `entity_config`）
  - `update_component`: 更新实体组件参数
- Godot → 后端
  - `sync_state`: 全场景实体状态上报
  - `ping`: 心跳

## 项目结构（关键部分）

```text
server.py
core/
  agent_core.py
  llm_providers.py
  memory_manager.py
  project_manager.py
frontend/src/
  App.vue
  components/
    AIControlPanel.vue
    GameStage.vue
    AssetPanel.vue
godot_project/
  scripts/LiveLink.gd
  components/*.gd
  assets/sprites/
stage_save.json
```

## 已知事项

- 当前环境下 `npm run build` 可能受 `vue-tsc` 与 Node 24 兼容影响。
- 如遇构建报错，建议使用 Node 20/22 LTS 进行前端构建。

## 许可证

MIT License
