# AI-Game-Builder

> 版本: 0.1.0 | AI 驱动的 Godot 4 游戏装配与实时可视化控制台

一个面向 Godot 4.x 的全栈 AI 游戏开发工作台，覆盖「创意 → 美术 → 实体装配 → 场景运行与调参」全流程。

## 核心能力

- 🤖 多模型 AI 驱动（DeepSeek / GPT / Claude / Ollama）
- 🧠 三模式工作流（创意助理 / 实体工坊 / 美术中心）
- 🧩 视觉化拼装流水线（素材点选 -> 工坊自动填充 -> 一键生成）
- 🌍 世界设置（背景图、背景色、重力）实时下发并持久化
- 🔄 WebSocket 实时联动（实体生成、组件热更、场景全局配置）
- 📡 场景状态闭环（Godot 上报 -> 后端记忆 -> 前端热区映射）
- 💾 场景断线恢复（实体与全局配置重连自动回放）
- 🚀 一键点亮舞台（前端启动 run_stage.py 导出并拉起 8060 Web 服务）
- 🩺 舞台自检面板（GODOT_PATH / Export Preset / 端口监听一键检查）

## 系统架构

```text
Vue 前端控制台
  ├─ 左侧 AI 控制舱（模式/模型/工坊/对话）
  ├─ 中间 Godot 挂载区（网格占位/实时画面 + 热区选中）
  └─ 右侧资产与世界设置（素材库/Inspector/全局配置）
        ↓
FastAPI 中枢（LLM 调度 + REST API + WebSocket）
        ↓
Godot LiveLink（实体装配、组件热更、全局场景应用）
        ↓
scene_state / stage_save.json（状态同步与持久化）
```

## 当前功能总览

### 1) 三模式 AI 工作流
- `chat`：创意助理，适合剧情、玩法、世界观与数值讨论。
- `build`：实体工坊，支持生成实体、增量热更组件参数、视觉化直连组装。
- `art`：美术中心，支持提示词优化与图片生成入库。

### 2) 视觉化组装（Visual Assembly）
- 在素材库点选图片后自动高亮“已选中”。
- 工坊自动显示装配预览，并自动将实体名填充为素材文件名（去后缀）。
- 点击「一键视觉化组装」时，若已有选中素材，会跳过 LLM 解析，直接调用：
  - `sprite_path`（由选中素材生成）
  - `required_components`（当前勾选组件）
  - 发送 `POST /api/generate_entity`（`direct_assembly=true`）

### 3) 场景全局配置（Scene Global Config）
- 支持配置并应用：
  - `background_image`
  - `background_color`
  - `physics_gravity`
- 后端接口：`POST /api/scene/config`
- 持久化到 `stage_save.json > global_config`
- 广播 WebSocket 动作：`update_scene_config`

### 4) 中间实时渲染挂载区
- 可在「网格占位」和「实时画面」切换。
- 实时画面默认 iframe 地址：`http://localhost:8060`（用于 Godot Web 导出）。
- 中间区带 Live Link 状态灯：
  - 绿色：`Live Link Active`
  - 红色：`Live Link Offline`
- 连接异常会显示兜底提示卡片，可直接重试或切换本地预览。

### 5) 实体热区点击联动
- 前端基于 `scene_state.entities[].x/y` 绘制透明热区。
- 点击热区会自动选中实体，并同步到实体工坊属性预览区。
- 坐标映射采用百分比映射并带边界钳制，兼容不同视口尺寸。

### 6) 场景状态同步与恢复
- Godot `sync_state` 上报包含：
  - `entities`（含组件参数）
  - `x/y`（实体全局坐标）
  - `viewport_width/viewport_height`（视口尺寸）
- 后端写入 `memory_manager.current_scene_state`。
- Godot 重连后自动恢复：
  - `update_scene_config`（全局配置）
  - `spawn_entity`（存档实体）

### 7) 舞台点亮与自检
- 系统设置支持配置：
  - `GODOT_PATH`
  - `Web 端口`
  - `导出预设`
  - `跳过导出`
- 提供「导出预设自检」按钮，返回三项状态：
  - `GODOT_PATH OK / Missing`
  - `Export Preset OK / Missing`
  - `<端口> Listening OK / Not Listening`
- 提供「启动 run_stage.py（点亮舞台）」按钮，自动触发 Godot Web 导出与 8060 服务启动。

## stage_save.json 结构

```json
{
  "entities": {
    "EntityName": {
      "entity_name": "EntityName",
      "base_type": "CharacterBody2D",
      "components": [],
      "component_params": {},
      "sprite_path": "res://assets/sprites/xxx.png",
      "metadata": {}
    }
  },
  "global_config": {
    "background_image": "",
    "background_color": "#0f172a",
    "physics_gravity": 980.0
  }
}
```

## 快速开始

### 1) 安装依赖

```bash
# Backend
pip install fastapi uvicorn pydantic websockets openai python-dotenv

# Frontend
cd frontend
npm install
```

### 2) 启动后端

```bash
python server.py
# http://localhost:8000
```

### 3) 启动前端

```bash
cd frontend
npm run dev
# http://localhost:1420
```

### 4) 启动 Godot

- 在前端「系统设置」配置 Godot 可执行文件路径，点击启动；或直接在 Godot 中打开 `godot_project`。
- LiveLink 连接地址：`ws://127.0.0.1:8000/ws`

### 5) 可选：启动 Godot Web 导出服务

- 用于中间区「实时画面」iframe 预览，默认地址 `http://localhost:8060`。
- 推荐直接在前端「系统设置」点击「启动 run_stage.py（点亮舞台）」。
- 也可命令行手动启动：

```bash
python run_stage.py --port 8060 --preset Web
```

常用参数：
- `--godot-path "D:\Softwares\Godot\Godot_v4.x.exe"`：指定 Godot 可执行文件
- `--skip-export`：跳过导出，仅启动 `web_build/` 静态服务

## API 速览

| 接口 | 方法 | 说明 |
|---|---|---|
| `/health` | GET | 服务健康状态（含 WebSocket 连接数） |
| `/api/generate_entity` | POST | chat/build/art 统一入口（含 direct assembly） |
| `/api/scene_state` | GET | 获取实时场景状态 |
| `/api/scene/config` | POST | 更新场景全局配置并广播 |
| `/api/assets/list` | GET | 获取贴图与组件列表 |
| `/api/config` | POST | 保存 DeepSeek API Key |
| `/api/chat/history` | GET | 获取聊天历史 |
| `/api/chat/clear` | POST | 清空聊天历史 |
| `/api/test_image_provider` | POST | 测试图像提供者连接 |
| `/api/launch_godot` | POST | 启动 Godot 编辑器 |
| `/api/system/godot_path` | GET/POST | 读取/保存 GODOT_PATH |
| `/api/stage/precheck` | GET | 舞台自检（路径/预设/端口） |
| `/api/stage/activate` | POST | 启动 run_stage.py |
| `/api/stage/status` | GET | 查询舞台服务进程状态 |
| `/api/system/select_file` | GET | 调起系统文件选择器 |
| `/ws` | WebSocket | Godot 实时通信通道 |

## WebSocket 协议

- 后端 -> Godot
  - `spawn_entity`
  - `update_component`
  - `update_scene_config`
- Godot -> 后端
  - `sync_state`
  - `ping`
- 前端 -> 后端
  - `ping`（心跳）
- 后端 -> 前端
  - `pong`
  - `engine_ready`

## 关键目录

```text
server.py
stage_save.json
core/
frontend/src/
  App.vue
  components/
    AIControlPanel.vue
    EntityWorkshop.vue
    AssetPanel.vue
    GameStage.vue
godot_project/
  scripts/LiveLink.gd
  components/*.gd
  assets/sprites/
```

## 文档

- 使用手册：见 [使用文档.md](./使用文档.md)
- 推荐顺序：
  1. 快速开始（本文件）
  2. 操作与排错（使用文档）

## 已知事项

- 当前环境下 `npm run build` 可能受 `vue-tsc` 与 Node 24 兼容影响。
- 已验证 `npx vite build` 可正常完成前端打包。

## 许可证

MIT License
