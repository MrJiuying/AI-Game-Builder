<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import axios from 'axios'
import AIControlPanel from './components/AIControlPanel.vue'
import GameStage from './components/GameStage.vue'
import AssetPanel from './components/AssetPanel.vue'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface GameAsset {
  id: number
  name: string
  url: string
}

interface SelectedSprite {
  name: string
  url: string
}

interface SceneEntity {
  name: string
  x?: number
  y?: number
  position?: { x?: number; y?: number }
  components?: Record<string, Record<string, any>>
}

interface EntityProperty {
  name: string
  value: number
  min: number
  max: number
}

const chatMessages = ref<ChatMessage[]>([
  {
    id: 1,
    role: 'assistant',
    content: '你好！我是 AI Game Builder 助手。描述你想要创建的游戏角色或场景，我会帮你自动生成 Godot 实体配置。',
    timestamp: new Date()
  }
])

const currentModel = ref('deepseek')
const apiKey = ref('')
const inputMessage = ref('')
const selectedGameType = ref('top_down_rpg')
const currentMode = ref('build')
const isLoading = ref(false)
const selectedImageProvider = ref('local_sd')
const customLora = ref('')
const artApiKey = ref('')
const artBaseUrl = ref('')
const isTesting = ref(false)
const testStatus = ref<{ status: 'idle' | 'success' | 'error'; message: string }>({ status: 'idle', message: '' })

const imageProviders = [
  { id: 'local_sd', name: '本地 SD WebUI' },
  { id: 'dalle3', name: 'DALL-E 3 云端' },
  { id: 'cloud_sd', name: '云端 Serverless SD' },
]

const gameAssets = ref<GameAsset[]>([])
const abilityComponents = ref<string[]>([])
const currentSelectedSprite = ref<SelectedSprite | null>(null)

const entityProperties = ref<EntityProperty[]>([
  { name: '移动速度 (Speed)', value: 300, min: 0, max: 1000 },
  { name: '最大血量 (Health)', value: 100, min: 1, max: 500 },
])

const selectedEntity = ref('TestPlayer')
const renderView = ref<'grid' | 'live'>('grid')
const godotWebUrl = ref('http://localhost:8060')
const godotIframeRef = ref<HTMLIFrameElement | null>(null)
const liveFrameNonce = ref(0)
const iframeLoadState = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
const iframeErrorMessage = ref('')
const engineLiveActive = ref(false)
const isPlaying = ref(false)
const isGodotLaunched = ref(false)
const showGodotWarning = ref(false)
const godotWarningTimer = ref<number | null>(null)
const engineWebSocket = ref<WebSocket | null>(null)
const wsHeartbeatTimer = ref<number | null>(null)
const wsLastPongAt = ref(0)
const selectedComponents = ref<string[]>([])
const showSettingsModal = ref(false)
const godotExePath = ref(localStorage.getItem('godot_path') || '')
const stagePort = ref<number>(Number(localStorage.getItem('stage_port') || 8060))
const stagePreset = ref(localStorage.getItem('stage_preset') || 'Web')
const skipStageExport = ref(false)
const stageActionStatus = ref('')
const isActivatingStage = ref(false)
const isCheckingStage = ref(false)
const stageCheckStatus = ref('')
const stageChecks = ref<{
  godot_path_ok: boolean
  export_preset_ok: boolean
  port_listening_ok: boolean
} | null>(null)
const sceneState = ref<Record<string, any>>({})
const sceneStatePollTimer = ref<number | null>(null)
const worldConfig = ref({
  background_image: '',
  background_color: '#0f172a',
  physics_gravity: 980,
})
const worldConfigStatus = ref('')
const scenePollIntervalMs = 3000

onMounted(async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/api/chat/history?mode=${currentMode.value}`)
    const data = await res.json()
    if (data.status === 'success' && data.history && data.history.length > 0) {
      chatMessages.value = data.history.map((m: any, idx: number) => ({
        id: idx,
        role: m.role,
        content: m.content,
        timestamp: new Date()
      }))
    } else {
      chatMessages.value = [{
        id: 1,
        role: 'assistant',
        content: getWelcomeMessage(currentMode.value),
        timestamp: new Date()
      }]
    }
  } catch (e) {
    console.error('加载聊天历史失败:', e)
  }
})

const clearHistory = async () => {
  try {
    await fetch(`${API_BASE_URL}/api/chat/clear?mode=${currentMode.value}`, { method: 'POST' })
    chatMessages.value = [{
      id: 1,
      role: 'assistant',
      content: getWelcomeMessage(currentMode.value),
      timestamp: new Date()
    }]
  } catch (e) {
    console.error('清空聊天历史失败:', e)
  }
}

const getWelcomeMessage = (mode: string) => {
  switch (mode) {
    case 'chat': return '💡 你好！我是创意助理。有什么游戏设定、剧情构思或数值平衡的问题，尽管问我！'
    case 'art': return '🎨 你好！我是美术中心。描述你想生成的图像，我会帮你优化提示词并生成图片！'
    default: return '🛠️ 你好！我是实体工坊。描述你想构建的游戏角色，我会帮你生成配置并装配到 Godot 中！'
  }
}

watch(currentMode, async (newMode) => {
  try {
    const res = await fetch(`${API_BASE_URL}/api/chat/history?mode=${newMode}`)
    const data = await res.json()
    if (data.status === 'success') {
      if (data.history && data.history.length > 0) {
        chatMessages.value = data.history.map((m: any, idx: number) => ({
          id: idx,
          role: m.role,
          content: m.content,
          timestamp: new Date()
        }))
      } else {
        chatMessages.value = [{
          id: 1,
          role: 'assistant',
          content: getWelcomeMessage(newMode),
          timestamp: new Date()
        }]
      }
    }
  } catch (e) {
    console.error('加载聊天历史失败:', e)
  }
})

const gameTypes = [
  { id: 'top_down_rpg', name: '俯视角 RPG', icon: '🗡️' },
  { id: 'platformer', name: '横版跳跃', icon: '🏃' },
  { id: 'top_down_shooter', name: '俯视角射击', icon: '🔫' },
  { id: 'tower_defense', name: '塔防', icon: '🏰' },
  { id: 'roguelike', name: 'Roguelike', icon: '🧭' },
  { id: 'survival', name: '生存', icon: '🔥' },
  { id: 'strategy', name: '策略', icon: '♟️' },
  { id: 'galgame_avg', name: 'Galgame/AVG', icon: '🌸' },
]

const defaultModels = [
  { id: 'deepseek', name: 'DeepSeek', api_key: '', base_url: '' },
  { id: 'claude', name: 'Claude', api_key: '', base_url: '' },
  { id: 'ollama', name: '本地 Ollama', api_key: '', base_url: 'http://localhost:11434' },
  { id: 'gpt4', name: 'GPT-4', api_key: '', base_url: '' },
]

const loadModelsFromStorage = () => {
  const saved = localStorage.getItem('llm_models')
  if (saved) {
    try {
      return JSON.parse(saved)
    } catch {
      return defaultModels
    }
  }
  return defaultModels
}

const llmModels = ref(loadModelsFromStorage())

const saveModelsToStorage = () => {
  localStorage.setItem('llm_models', JSON.stringify(llmModels.value))
}

const currentModelConfig = computed(() => {
  return llmModels.value.find(m => m.id === currentModel.value)
})

watch(
  [currentModel, llmModels],
  () => {
    const model = llmModels.value.find(m => m.id === currentModel.value)
    apiKey.value = model?.api_key || ''
  },
  { immediate: true, deep: true }
)

const showAddModelModal = ref(false)
const newModelForm = ref({ id: '', name: '', api_key: '', base_url: '' })

const addModel = () => {
  if (!newModelForm.value.id || !newModelForm.value.name) return
  llmModels.value.push({ ...newModelForm.value })
  saveModelsToStorage()
  currentModel.value = newModelForm.value.id
  showAddModelModal.value = false
  newModelForm.value = { id: '', name: '', api_key: '', base_url: '' }
}

const isModelConfigured = computed(() => {
  const config = currentModelConfig.value
  if (!config) return false
  if (config.id === 'ollama') return true
  return !!config.api_key
})

const API_BASE_URL = 'http://localhost:8000'

const sceneEntities = computed<SceneEntity[]>(() => {
  const entities = sceneState.value?.entities
  return Array.isArray(entities) ? entities : []
})

const selectedEntitySnapshot = computed<SceneEntity | null>(() => {
  const target = sceneEntities.value.find(entity => entity?.name === selectedEntity.value)
  return target || sceneEntities.value[0] || null
})

const normalizeEntityPosition = (entity: SceneEntity) => {
  const rawX = Number(entity?.x ?? entity?.position?.x ?? 0)
  const rawY = Number(entity?.y ?? entity?.position?.y ?? 0)
  return {
    x: Number.isFinite(rawX) ? rawX : 0,
    y: Number.isFinite(rawY) ? rawY : 0,
  }
}

const entityHotspots = computed(() => {
  const sourceWidth = Number(
    sceneState.value?.viewport_width ??
    sceneState.value?.stage_width ??
    sceneState.value?.width ??
    1280
  )
  const sourceHeight = Number(
    sceneState.value?.viewport_height ??
    sceneState.value?.stage_height ??
    sceneState.value?.height ??
    720
  )
  const safeWidth = sourceWidth > 0 ? sourceWidth : 1280
  const safeHeight = sourceHeight > 0 ? sourceHeight : 720

  return sceneEntities.value.map((entity, index) => {
    const pos = normalizeEntityPosition(entity)
    const xPct = Math.max(0, Math.min(100, (pos.x / safeWidth) * 100))
    const yPct = Math.max(0, Math.min(100, (pos.y / safeHeight) * 100))
    return {
      id: `${entity.name || 'entity'}-${index}`,
      name: entity.name || `Entity_${index + 1}`,
      left: `${xPct}%`,
      top: `${yPct}%`,
      rawX: pos.x,
      rawY: pos.y,
    }
  })
})

const fetchEngineStatus = async () => {
  try {
    const { data } = await axios.get(`${API_BASE_URL}/health`)
    const connections = Number(data?.websocket_connections ?? 0)
    engineLiveActive.value = Number.isFinite(connections) && connections > 0
  } catch {
    engineLiveActive.value = false
  }
}

const fetchSceneState = async () => {
  try {
    const { data } = await axios.get(`${API_BASE_URL}/api/scene_state`)
    sceneState.value = data && typeof data === 'object' ? data : {}
    if (sceneEntities.value.length > 0) {
      const found = sceneEntities.value.some(entity => entity?.name === selectedEntity.value)
      if (!found) {
        selectedEntity.value = sceneEntities.value[0].name || selectedEntity.value
      }
    }
  } catch {
    sceneState.value = {}
  }
}

const fetchAssets = async () => {
  try {
    const { data } = await axios.get(`${API_BASE_URL}/api/assets/list`)
    const sprites = Array.isArray(data?.sprites) ? data.sprites : []
    const components = Array.isArray(data?.components) ? data.components : []
    gameAssets.value = sprites.map((item: any, index: number) => ({
      id: index + 1,
      name: item.name || `sprite_${index + 1}`,
      url: `${API_BASE_URL}${item.url || ''}`,
    }))
    abilityComponents.value = components.map((item: any) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object' && item.name) {
        return item.category ? `${item.category}:${item.name}` : item.name
      }
      return ''
    }).filter(Boolean)
    if (currentSelectedSprite.value) {
      const stillExists = gameAssets.value.some(asset => asset.name === currentSelectedSprite.value?.name)
      if (!stillExists) {
        currentSelectedSprite.value = null
      }
    }
  } catch {
    gameAssets.value = []
    abilityComponents.value = []
    currentSelectedSprite.value = null
  }
}

const handleSelectSprite = (asset: SelectedSprite) => {
  currentSelectedSprite.value = asset
  worldConfig.value.background_image = `res://assets/sprites/${asset.name}`
}

const handleSelectEntityFromStage = (entityName: string) => {
  if (!entityName) return
  selectedEntity.value = entityName
}

const checkGodotWebAvailability = async () => {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => {
    controller.abort()
  }, 1200)
  try {
    await fetch(`${godotWebUrl.value}?_ts=${Date.now()}`, {
      mode: 'no-cors',
      cache: 'no-store',
      signal: controller.signal,
    })
    return true
  } catch {
    return false
  } finally {
    clearTimeout(timeoutId)
  }
}

const startLiveRenderProbe = async () => {
  if (renderView.value !== 'live') return
  iframeLoadState.value = 'loading'
  iframeErrorMessage.value = ''
  const reachable = await checkGodotWebAvailability()
  if (!reachable) {
    iframeLoadState.value = 'error'
    iframeErrorMessage.value = '无法连接到 http://localhost:8060，请先启动 Godot Web 服务。'
    return
  }
  liveFrameNonce.value += 1
}

const handleIframeLoaded = () => {
  if (renderView.value !== 'live') return
  iframeLoadState.value = 'ready'
  iframeErrorMessage.value = ''
}

const handleIframeLoadError = () => {
  if (renderView.value !== 'live') return
  iframeLoadState.value = 'error'
  iframeErrorMessage.value = '实时画面加载失败，请确认 8060 端口服务可访问。'
}

const connectEngineWebSocket = () => {
  if (engineWebSocket.value && (engineWebSocket.value.readyState === WebSocket.OPEN || engineWebSocket.value.readyState === WebSocket.CONNECTING)) {
    return
  }
  const ws = new WebSocket('ws://127.0.0.1:8000/ws')
  engineWebSocket.value = ws
  ws.onopen = () => {
    wsLastPongAt.value = Date.now()
    if (wsHeartbeatTimer.value) {
      clearInterval(wsHeartbeatTimer.value)
      wsHeartbeatTimer.value = null
    }
    wsHeartbeatTimer.value = window.setInterval(() => {
      if (!engineWebSocket.value || engineWebSocket.value.readyState !== WebSocket.OPEN) {
        return
      }
      if (Date.now() - wsLastPongAt.value > 15000) {
        engineWebSocket.value.close()
        return
      }
      engineWebSocket.value.send(JSON.stringify({ action: 'ping', source: 'frontend' }))
    }, 5000)
  }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data?.action === 'pong') {
        wsLastPongAt.value = Date.now()
        return
      }
      if (data?.action !== 'engine_ready') return
      const stageUrl = typeof data?.stage_url === 'string' && data.stage_url ? data.stage_url : godotWebUrl.value
      godotWebUrl.value = stageUrl
      engineLiveActive.value = true
      console.info('收到 engine_ready 信号:', data)
      if (renderView.value === 'live') {
        startLiveRenderProbe()
      }
    } catch {}
  }
  ws.onclose = () => {
    if (wsHeartbeatTimer.value) {
      clearInterval(wsHeartbeatTimer.value)
      wsHeartbeatTimer.value = null
    }
    window.setTimeout(() => {
      connectEngineWebSocket()
    }, 1200)
  }
  ws.onerror = () => {
    ws.close()
  }
}

const applyWorldConfig = async () => {
  worldConfigStatus.value = '正在应用世界设置...'
  const payload = {
    background_image: worldConfig.value.background_image || undefined,
    background_color: worldConfig.value.background_color || undefined,
    physics_gravity: Number.isFinite(worldConfig.value.physics_gravity)
      ? worldConfig.value.physics_gravity
      : undefined,
  }
  const sceneCommand = {
    action: 'update_scene_config',
    config: payload,
  }
  console.info('下发给 Godot 的场景配置指令:', JSON.stringify(sceneCommand, null, 2))
  try {
    const { data } = await axios.post(`${API_BASE_URL}/api/scene/config`, payload)
    if (data?.status === 'success') {
      worldConfigStatus.value = '已应用到场景'
    } else {
      worldConfigStatus.value = '应用失败'
    }
  } catch {
    worldConfigStatus.value = '应用失败'
  }
  window.setTimeout(() => {
    worldConfigStatus.value = ''
  }, 1800)
}

const saveApiKeyConfig = async (value: string) => {
  if (currentModel.value !== 'deepseek') return
  const key = value.trim()
  if (!key) return

  try {
    const response = await fetch(`${API_BASE_URL}/api/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        deepseek_api_key: key
      })
    })
    const result = await response.json()
    if (response.ok && result.status === 'success') {
      console.info('DeepSeek API Key 保存成功')
    } else {
      alert(`保存失败: ${result.detail || result.message || '未知错误'}`)
    }
  } catch (error) {
    alert(`保存失败: ${error instanceof Error ? error.message : '网络错误'}`)
  }
}

const performGenerate = async (
  prompt: string,
  options: { mode?: string; requiredComponents?: string[]; userVisibleText?: string } = {}
) => {
  if (!prompt.trim() || isLoading.value) return
  if (!isModelConfigured.value) {
    alert('⚠️ 请先选择并配置模型 API Key')
    return
  }
  const modeToUse = options.mode || currentMode.value
  const requiredComponents = options.requiredComponents || selectedComponents.value
  const userVisibleText = options.userVisibleText || prompt

  const userMsg: ChatMessage = {
    id: Date.now(),
    role: 'user',
    content: userVisibleText,
    timestamp: new Date()
  }
  chatMessages.value.push(userMsg)

  const userInput = prompt
  if (!options.userVisibleText || options.userVisibleText === inputMessage.value) {
    inputMessage.value = ''
  }
  isLoading.value = true

  const loadingMsgId = Date.now() + 1
  const providerName = imageProviders.find(p => p.id === selectedImageProvider.value)?.name || selectedImageProvider.value
  const loadingMsg: ChatMessage = {
    id: loadingMsgId,
    role: 'assistant',
    content: `⏳ 正在调度 [${providerName}] 渲染专属视觉资产，请稍候...`,
    timestamp: new Date()
  }
  chatMessages.value.push(loadingMsg)

  try {
    const response = await fetch(`${API_BASE_URL}/api/generate_entity`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: userInput,
        mode: modeToUse,
        model_name: currentModel.value,
        api_key: apiKey.value || undefined,
        image_provider: selectedImageProvider.value,
        lora_model: customLora.value || undefined,
        art_api_key: artApiKey.value || undefined,
        art_base_url: artBaseUrl.value || undefined,
        game_base: selectedGameType.value,
        required_components: requiredComponents
      })
    })

    const result = await response.json()

    const loadingIndex = chatMessages.value.findIndex(m => m.id === loadingMsgId)
    if (loadingIndex !== -1) {
      if (response.ok && result.status === 'success') {
        let content = ''
        if (modeToUse === 'chat') {
          content = result.text_reply || result.message || ''
        } else if (modeToUse === 'art') {
          content = result.message || result.text_reply || ''
        } else {
          content = result.message || `✅ 实体 [${result.entity_name}] 装配成功！配置文件已送达引擎目录。\n\n📁 配置路径: ${result.config_path}`
        }
        
        chatMessages.value[loadingIndex] = {
          id: loadingMsgId,
          role: 'assistant',
          content: content,
          timestamp: new Date()
        }
      } else {
        const errorMessage = result.error || result.message || '未知错误'
        chatMessages.value[loadingIndex] = {
          id: loadingMsgId,
          role: 'assistant',
          content: `❌ 生成失败: ${errorMessage}`,
          timestamp: new Date()
        }
      }
    }
  } catch (error) {
    const loadingIndex = chatMessages.value.findIndex(m => m.id === loadingMsgId)
    if (loadingIndex !== -1) {
      chatMessages.value[loadingIndex] = {
        id: loadingMsgId,
        role: 'assistant',
        content: `❌ 网络错误: ${error instanceof Error ? error.message : '无法连接到后端服务'}`,
        timestamp: new Date()
      }
    }
  }

  isLoading.value = false
}

const sendMessage = async () => {
  await performGenerate(inputMessage.value)
}

const performVisualAssembly = async (payload: { prompt: string; entityName: string; spriteName?: string }) => {
  if (isLoading.value) return
  if (!payload.spriteName) {
    await performGenerate(payload.prompt, {
      mode: 'build',
      requiredComponents: selectedComponents.value
    })
    return
  }
  if (!isModelConfigured.value) {
    alert('⚠️ 请先选择并配置模型 API Key')
    return
  }

  const userVisibleText = `🧩 视觉化组装 -> ${payload.entityName}\n贴图: ${payload.spriteName}\n组件: ${selectedComponents.value.join('、') || '无'}`
  const userMsg: ChatMessage = {
    id: Date.now(),
    role: 'user',
    content: userVisibleText,
    timestamp: new Date()
  }
  chatMessages.value.push(userMsg)
  isLoading.value = true

  const loadingMsgId = Date.now() + 1
  chatMessages.value.push({
    id: loadingMsgId,
    role: 'assistant',
    content: '⏳ 正在执行视觉化组装流水线...',
    timestamp: new Date()
  })

  try {
    const response = await fetch(`${API_BASE_URL}/api/generate_entity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: payload.prompt,
        mode: 'build',
        model_name: currentModel.value,
        api_key: apiKey.value || undefined,
        game_base: selectedGameType.value,
        required_components: selectedComponents.value,
        direct_assembly: true,
        entity_name: payload.entityName,
        sprite_name: payload.spriteName,
      })
    })
    const result = await response.json()
    const loadingIndex = chatMessages.value.findIndex(m => m.id === loadingMsgId)
    if (loadingIndex !== -1) {
      chatMessages.value[loadingIndex] = {
        id: loadingMsgId,
        role: 'assistant',
        content: response.ok && result.status === 'success'
          ? (result.message || `✅ 实体 [${result.entity_name}] 视觉化组装完成`)
          : `❌ 视觉化组装失败: ${result.error || result.message || '未知错误'}`,
        timestamp: new Date()
      }
    }
  } catch (error) {
    const loadingIndex = chatMessages.value.findIndex(m => m.id === loadingMsgId)
    if (loadingIndex !== -1) {
      chatMessages.value[loadingIndex] = {
        id: loadingMsgId,
        role: 'assistant',
        content: `❌ 视觉化组装失败: ${error instanceof Error ? error.message : '网络错误'}`,
        timestamp: new Date()
      }
    }
  }
  isLoading.value = false
}

const handleWorkshopGenerate = async (payload: { prompt: string; entityName: string; directAssembly: boolean; spriteName?: string }) => {
  if (payload.directAssembly) {
    await performVisualAssembly(payload)
    return
  }
  await performGenerate(payload.prompt, {
    mode: 'build',
    requiredComponents: selectedComponents.value
  })
}

const handleQuickDialogueUpdate = async (dialogueText: string) => {
  const lines = dialogueText
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
  if (lines.length === 0) return

  const prompt = `请把实体 ${selectedEntity.value} 的 DialoguePlayerComponent 更新为以下对白，每行一条：${lines.join(' | ')}`
  await performGenerate(prompt, {
    mode: 'build',
    requiredComponents: ['DialoguePlayerComponent'],
    userVisibleText: `💬 快速对白更新 -> ${selectedEntity.value}\n${lines.join('\n')}`
  })
}

const testImageProvider = async () => {
  isTesting.value = true
  testStatus.value = { status: 'idle', message: '' }

  try {
    const response = await fetch(`${API_BASE_URL}/api/test_image_provider`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        provider_name: selectedImageProvider.value,
        api_key: artApiKey.value || undefined,
        base_url: artBaseUrl.value || undefined
      })
    })

    const result = await response.json()

    if (response.ok) {
      if (result.status === 'success') {
        testStatus.value = { status: 'success', message: result.message }
      } else {
        testStatus.value = { status: 'error', message: result.message }
      }
    } else {
      testStatus.value = { status: 'error', message: result.message || '请求失败' }
    }
  } catch (error) {
    testStatus.value = { status: 'error', message: error instanceof Error ? error.message : '网络错误' }
  } finally {
    isLoading.value = false
    isTesting.value = false
  }
}

const togglePlay = () => {
  isPlaying.value = !isPlaying.value
}

const handlePropertyChange = (propertyName: string, newValue: number) => {
  const prop = entityProperties.value.find(p => p.name === propertyName)
  if (prop) {
    prop.value = newValue
  }
}

const launchGodot = async () => {
  if (!godotExePath.value) {
    alert('请先在系统设置中配置 Godot 引擎的可执行文件路径！')
    showSettingsModal.value = true
    return
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/launch_godot`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        godot_path: godotExePath.value
      })
    })
    
    const result = await response.json()
    
    if (response.ok && result.status === 'success') {
      isGodotLaunched.value = true
    } else {
      alert(`启动 Godot 失败: ${result.message}`)
    }
  } catch (error) {
    alert(`启动 Godot 失败: ${error instanceof Error ? error.message : '网络错误'}`)
  }
}

const activateStage = async () => {
  isActivatingStage.value = true
  stageActionStatus.value = '正在启动 Godot Web Activator...'
  const portValue = Number(stagePort.value)
  if (!Number.isFinite(portValue) || portValue <= 0) {
    stageActionStatus.value = '端口无效'
    isActivatingStage.value = false
    return
  }
  try {
    const response = await fetch(`${API_BASE_URL}/api/stage/activate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        godot_path: godotExePath.value || undefined,
        port: portValue,
        preset: stagePreset.value || 'Web',
        skip_export: skipStageExport.value,
      })
    })
    const result = await response.json()
    if (response.ok && result.status === 'success') {
      godotWebUrl.value = `http://localhost:${portValue}`
      renderView.value = 'live'
      stageActionStatus.value = `已触发启动（PID: ${result.pid ?? '未知'}）`
      console.info('Godot Web Activator 启动结果:', result)
      startLiveRenderProbe()
    } else {
      stageActionStatus.value = `启动失败: ${result.detail || result.message || '未知错误'}`
    }
  } catch (error) {
    stageActionStatus.value = `启动失败: ${error instanceof Error ? error.message : '网络错误'}`
  } finally {
    isActivatingStage.value = false
  }
}

const runStagePrecheck = async () => {
  isCheckingStage.value = true
  stageCheckStatus.value = '正在执行自检...'
  stageChecks.value = null
  const portValue = Number(stagePort.value)
  const params = new URLSearchParams({
    port: String(Number.isFinite(portValue) ? portValue : 8060),
    preset: stagePreset.value || 'Web'
  })
  try {
    const response = await fetch(`${API_BASE_URL}/api/stage/precheck?${params.toString()}`)
    const result = await response.json()
    if (response.ok && result.status === 'success') {
      stageChecks.value = result.checks || null
      const checks = result.checks || {}
      const allOk = !!checks.godot_path_ok && !!checks.export_preset_ok && !!checks.port_listening_ok
      stageCheckStatus.value = allOk ? '全部通过，可直接点亮舞台。' : '存在未通过项，请按红色项修复。'
    } else {
      stageCheckStatus.value = `自检失败: ${result.detail || result.message || '未知错误'}`
    }
  } catch (error) {
    stageCheckStatus.value = `自检失败: ${error instanceof Error ? error.message : '网络错误'}`
  } finally {
    isCheckingStage.value = false
  }
}

const loadGodotPathFromBackend = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/system/godot_path`)
    const result = await response.json()
    if (response.ok && result.status === 'success' && result.godot_path) {
      godotExePath.value = result.godot_path
      localStorage.setItem('godot_path', result.godot_path)
    }
  } catch {}
}

const saveSettings = async () => {
  const normalizedPort = Number(stagePort.value)
  localStorage.setItem('godot_path', godotExePath.value)
  localStorage.setItem('stage_port', String(Number.isFinite(normalizedPort) ? normalizedPort : 8060))
  localStorage.setItem('stage_preset', stagePreset.value || 'Web')
  if (Number.isFinite(normalizedPort) && normalizedPort > 0) {
    godotWebUrl.value = `http://localhost:${normalizedPort}`
  }
  if (godotExePath.value.trim()) {
    try {
      await fetch(`${API_BASE_URL}/api/system/godot_path`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          godot_path: godotExePath.value.trim()
        })
      })
    } catch (error) {
      console.error('保存 GODOT_PATH 失败:', error)
    }
  }
  showSettingsModal.value = false
}

const isSelectingFile = ref(false)

const selectGodotFile = async () => {
  isSelectingFile.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/api/system/select_file`)
    const result = await response.json()
    
    if (result.path) {
      godotExePath.value = result.path
    }
  } catch (error) {
    console.error('选择文件失败:', error)
  } finally {
    isSelectingFile.value = false
  }
}

const sendMessageWithCheck = async () => {
  // chat 和 art 模式下不检查 Godot 状态
  if (currentMode.value === 'build' && !isGodotLaunched.value) {
    // 显示非阻塞警告提示
    showGodotWarning.value = true
    if (godotWarningTimer.value) {
      clearTimeout(godotWarningTimer.value)
    }
    godotWarningTimer.value = window.setTimeout(() => {
      showGodotWarning.value = false
    }, 5000)
  }
  // 不阻止发送，让 AI 继续工作
  sendMessage()
}

watch(renderView, (nextView) => {
  if (nextView === 'live') {
    startLiveRenderProbe()
    return
  }
  iframeLoadState.value = 'idle'
  iframeErrorMessage.value = ''
})

onMounted(() => {
  connectEngineWebSocket()
  loadGodotPathFromBackend()
  runStagePrecheck()
  fetchAssets()
  fetchSceneState()
  fetchEngineStatus()
  sceneStatePollTimer.value = window.setInterval(() => {
    fetchSceneState()
    fetchEngineStatus()
    if (renderView.value === 'live' && iframeLoadState.value !== 'ready') {
      startLiveRenderProbe()
    }
  }, scenePollIntervalMs)
})

onBeforeUnmount(() => {
  if (sceneStatePollTimer.value) {
    clearInterval(sceneStatePollTimer.value)
    sceneStatePollTimer.value = null
  }
  if (engineWebSocket.value) {
    engineWebSocket.value.close()
    engineWebSocket.value = null
  }
  if (wsHeartbeatTimer.value) {
    clearInterval(wsHeartbeatTimer.value)
    wsHeartbeatTimer.value = null
  }
})
</script>

<template>
  <!-- 非阻塞警告提示 -->
  <div v-if="showGodotWarning" class="fixed top-4 left-1/2 -translate-x-1/2 z-50 animate-fade-in">
    <div class="bg-amber-900/90 border border-amber-500 text-amber-100 px-4 py-3 rounded-lg shadow-lg flex items-center gap-3">
      <span>⚠️</span>
      <span class="text-sm">Godot 预览未启动，本次生成的实体将保存在后台图纸中。随时可点击下方按钮启动预览。</span>
      <button @click="showGodotWarning = false" class="text-amber-300 hover:text-white">✕</button>
    </div>
  </div>

  <div class="h-screen w-screen flex bg-slate-950 text-gray-200 overflow-hidden">
    <!-- 左侧边栏：AI 核心控制舱 -->
    <aside class="w-1/4 min-w-[320px] flex flex-col bg-slate-900 border-r border-slate-700">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h1 class="text-lg font-bold text-cyan-400">🎮 AI Game Builder</h1>
        <button @click="clearHistory" class="text-xs text-slate-400 hover:text-red-400 transition-colors" title="清空记忆">
          🗑️
        </button>
      </div>
      <AIControlPanel
        class="flex-1 min-h-0"
        v-model:currentModel="currentModel"
        v-model:apiKey="apiKey"
        v-model:inputMessage="inputMessage"
        v-model:selectedGameType="selectedGameType"
        v-model:selectedComponents="selectedComponents"
        v-model:currentMode="currentMode"
        v-model:showAddModelModal="showAddModelModal"
        v-model:newModelForm="newModelForm"
        :selectedEntity="selectedEntity"
        :selectedEntitySnapshot="selectedEntitySnapshot"
        :currentSelectedSprite="currentSelectedSprite"
        :chatMessages="chatMessages"
        :isLoading="isLoading"
        :gameTypes="gameTypes"
        :llmModels="llmModels"
        :isModelConfigured="isModelConfigured"
        @send="sendMessageWithCheck"
        @generate-entity="handleWorkshopGenerate"
        @quick-dialogue-update="handleQuickDialogueUpdate"
        @addModel="addModel"
        @save-api-key="saveApiKeyConfig"
      />
    </aside>

    <!-- 中间主屏：可视化舞台 -->
    <main class="flex-1 flex flex-col bg-slate-950">
      <div class="px-4 py-3 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div :class="['w-2.5 h-2.5 rounded-full', engineLiveActive ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]' : 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.6)]']"></div>
          <div class="text-xs" :class="engineLiveActive ? 'text-emerald-300' : 'text-red-300'">
            {{ engineLiveActive ? 'Live Link Active' : 'Live Link Offline' }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="renderView = 'grid'"
            :class="[
              'px-3 py-1.5 rounded text-xs border transition-colors',
              renderView === 'grid' ? 'bg-blue-700 border-blue-500 text-white' : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
            ]"
          >
            网格占位
          </button>
          <button
            @click="renderView = 'live'"
            :class="[
              'px-3 py-1.5 rounded text-xs border transition-colors',
              renderView === 'live' ? 'bg-emerald-700 border-emerald-500 text-white' : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
            ]"
          >
            实时画面
          </button>
          <button
            @click="showSettingsModal = true"
            class="px-3 py-1.5 rounded text-xs border bg-slate-800 border-slate-600 text-slate-200 hover:bg-slate-700 transition-colors"
          >
            系统设置
          </button>
        </div>
      </div>

      <div class="relative flex-1 min-h-0">
        <GameStage
          v-if="renderView === 'grid'"
          :isPlaying="isPlaying"
          :isGodotLaunched="isGodotLaunched"
          @toggle-play="togglePlay"
          @launch-godot="launchGodot"
        />

        <div v-else class="relative h-full w-full bg-slate-900">
          <iframe
            ref="godotIframeRef"
            :key="liveFrameNonce"
            :src="godotWebUrl"
            title="Godot Web Runtime"
            class="w-full h-full border-0"
            allow="autoplay; fullscreen"
            @load="handleIframeLoaded"
            @error="handleIframeLoadError"
          />
          <div
            v-if="iframeLoadState === 'loading'"
            class="absolute inset-0 bg-slate-950/85 flex items-center justify-center"
          >
            <div class="text-center space-y-2">
              <div class="text-cyan-300 text-sm font-medium">正在连接 Godot Web 服务...</div>
              <div class="text-xs text-slate-400">地址：{{ godotWebUrl }}</div>
            </div>
          </div>
          <div
            v-if="iframeLoadState === 'error'"
            class="absolute inset-0 bg-slate-950/95 flex items-center justify-center p-6"
          >
            <div class="max-w-md w-full rounded-xl border border-red-700/60 bg-slate-900/90 p-5 text-center space-y-3">
              <div class="text-red-300 text-base font-semibold">⚠️ Godot 实时画面不可用</div>
              <div class="text-xs text-slate-300 leading-6">{{ iframeErrorMessage }}</div>
              <div class="flex items-center justify-center gap-2">
                <button
                  @click="startLiveRenderProbe"
                  class="px-3 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 text-xs text-white"
                >
                  重试连接
                </button>
                <button
                  @click="launchGodot"
                  class="px-3 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-xs text-white"
                >
                  运行本地预览
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="absolute inset-0 pointer-events-none">
          <button
            v-for="hotspot in entityHotspots"
            :key="hotspot.id"
            @click="handleSelectEntityFromStage(hotspot.name)"
            class="absolute pointer-events-auto -translate-x-1/2 -translate-y-1/2 px-2 py-1 rounded border text-[11px] transition-all duration-150"
            :class="[
              selectedEntity === hotspot.name
                ? 'border-cyan-300 bg-cyan-500/35 text-cyan-100 shadow-[0_0_16px_rgba(34,211,238,0.45)]'
                : 'border-white/40 bg-black/25 text-slate-100 hover:bg-cyan-500/25 hover:border-cyan-300'
            ]"
            :style="{ left: hotspot.left, top: hotspot.top }"
            :title="`${hotspot.name} (${Math.round(hotspot.rawX)}, ${Math.round(hotspot.rawY)})`"
          >
            {{ hotspot.name }}
          </button>
        </div>
      </div>
      <div class="px-4 py-2 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
        <div class="text-[11px] text-slate-400">如果 8060 端口未启动，可直接打开本地 Godot 预览窗口</div>
        <div class="flex items-center gap-2">
          <button
            @click="activateStage"
            :disabled="isActivatingStage"
            class="px-3 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 disabled:bg-slate-700 text-xs text-white transition-colors"
          >
            {{ isActivatingStage ? '点亮中...' : '一键点亮舞台' }}
          </button>
          <button
            @click="launchGodot"
            class="px-3 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-xs text-white transition-colors"
          >
            运行本地预览
          </button>
        </div>
      </div>
    </main>

    <!-- 右侧边栏：资产与属性工厂 -->
    <aside class="w-1/4 min-w-[320px] flex flex-col bg-slate-900 border-l border-slate-700">
      <div class="p-4 border-b border-slate-700 bg-slate-900/70">
        <div class="text-xs uppercase tracking-wider text-emerald-300 font-semibold mb-3">世界设置 (World Settings)</div>
        <div class="space-y-3">
          <div>
            <div class="text-xs text-slate-400 mb-1">背景预览</div>
            <div class="h-28 rounded border border-slate-700 bg-slate-950 flex items-center justify-center overflow-hidden">
              <img
                v-if="currentSelectedSprite"
                :src="currentSelectedSprite.url"
                :alt="currentSelectedSprite.name"
                class="max-w-full max-h-full object-contain"
              />
              <div v-else class="text-xs text-slate-500">点选素材库中的图片可快速设为背景</div>
            </div>
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">背景路径</label>
            <input
              v-model="worldConfig.background_image"
              type="text"
              placeholder="res://assets/sprites/background.png"
              class="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-xs text-slate-400 mb-1">背景色</label>
              <input v-model="worldConfig.background_color" type="color" class="w-full h-8 rounded bg-slate-800 border border-slate-600" />
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">重力</label>
              <input
                v-model.number="worldConfig.physics_gravity"
                type="number"
                min="0"
                step="10"
                class="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
          <button
            @click="applyWorldConfig"
            class="w-full py-2 bg-emerald-700 hover:bg-emerald-600 rounded text-xs text-white transition-colors"
          >
            应用世界配置
          </button>
          <div v-if="worldConfigStatus" class="text-xs text-emerald-300">{{ worldConfigStatus }}</div>
        </div>
      </div>
      <AssetPanel
        :assets="gameAssets"
        :abilityComponents="abilityComponents"
        :selectedSpriteName="currentSelectedSprite?.name || ''"
        :entityProperties="entityProperties"
        :selectedEntity="selectedEntity"
        :selectedImageProvider="selectedImageProvider"
        :customLora="customLora"
        :imageProviders="imageProviders"
        :artApiKey="artApiKey"
        :artBaseUrl="artBaseUrl"
        :sceneState="sceneState"
        :isTesting="isTesting"
        :testStatus="testStatus"
        @update-property="handlePropertyChange"
        @update:selectedImageProvider="selectedImageProvider = $event"
        @update:customLora="customLora = $event"
        @update:artApiKey="artApiKey = $event"
        @update:artBaseUrl="artBaseUrl = $event"
        @select-sprite="handleSelectSprite"
        @test-connection="testImageProvider"
      />
    </aside>
  </div>
  
  <!-- 设置按钮 -->
  <button
    @click="showSettingsModal = true"
    class="fixed bottom-4 right-4 z-[70] w-12 h-12 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center shadow-lg border border-slate-600 transition-colors duration-200"
    title="系统设置"
  >
    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-slate-400" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
    </svg>
  </button>
  
  <!-- 设置弹窗 -->
  <div v-if="showSettingsModal" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- 遮罩 -->
    <div class="absolute inset-0 bg-black/60" @click="showSettingsModal = false"></div>
    
    <!-- 弹窗内容 -->
    <div class="relative bg-slate-800 rounded-xl shadow-2xl border border-slate-700 w-full max-w-md p-6">
      <h2 class="text-xl font-semibold text-white mb-4 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
        </svg>
        系统设置
      </h2>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-slate-400 mb-2">Godot 引擎绝对路径 (.exe)</label>
          <div class="flex gap-2">
            <input
              v-model="godotExePath"
              type="text"
              placeholder="例如: D:\Softwares\Godot\Godot_v4.exe"
              class="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            <button
              @click="selectGodotFile"
              :disabled="isSelectingFile"
              class="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded-lg text-sm text-gray-200 transition-colors duration-200 flex items-center gap-2"
            >
              <span v-if="isSelectingFile" class="animate-spin">⏳</span>
              <span v-else>📁</span>
              浏览
            </button>
          </div>
          <p class="text-xs text-slate-500 mt-1">点击"浏览"按钮选择 Godot 可执行文件</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm text-slate-400 mb-2">Web 端口</label>
            <input
              v-model.number="stagePort"
              type="number"
              min="1"
              max="65535"
              class="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-2">导出预设</label>
            <input
              v-model="stagePreset"
              type="text"
              placeholder="Web"
              class="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>
        <label class="flex items-center gap-2 text-xs text-slate-400">
          <input v-model="skipStageExport" type="checkbox" class="accent-cyan-500" />
          跳过导出（仅启动 web_build 服务）
        </label>
        <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-3">
          <button
            @click="runStagePrecheck"
            :disabled="isCheckingStage"
            class="w-full py-2 bg-indigo-700 hover:bg-indigo-600 disabled:bg-slate-700 rounded-lg text-sm text-white transition-colors"
          >
            {{ isCheckingStage ? '正在自检...' : '导出预设自检' }}
          </button>
          <div v-if="stageCheckStatus" class="mt-2 text-xs text-slate-300 break-all">{{ stageCheckStatus }}</div>
          <div v-if="stageChecks" class="mt-2 space-y-1 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-400">GODOT_PATH</span>
              <span :class="stageChecks.godot_path_ok ? 'text-emerald-300' : 'text-red-300'">{{ stageChecks.godot_path_ok ? 'OK' : 'Missing' }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">Export Preset</span>
              <span :class="stageChecks.export_preset_ok ? 'text-emerald-300' : 'text-red-300'">{{ stageChecks.export_preset_ok ? 'OK' : 'Missing' }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">{{ stagePort }} Listening</span>
              <span :class="stageChecks.port_listening_ok ? 'text-emerald-300' : 'text-red-300'">{{ stageChecks.port_listening_ok ? 'OK' : 'Not Listening' }}</span>
            </div>
          </div>
        </div>
        <div class="rounded-lg border border-cyan-900/50 bg-slate-900/60 p-3">
          <button
            @click="activateStage"
            :disabled="isActivatingStage"
            class="w-full py-2 bg-cyan-700 hover:bg-cyan-600 disabled:bg-slate-700 rounded-lg text-sm text-white transition-colors"
          >
            {{ isActivatingStage ? '正在启动 Godot Web Activator...' : '启动 run_stage.py（点亮舞台）' }}
          </button>
          <div v-if="stageActionStatus" class="mt-2 text-xs text-cyan-300 break-all">{{ stageActionStatus }}</div>
        </div>
      </div>
      
      <div class="flex justify-end gap-3 mt-6">
        <button
          @click="showSettingsModal = false"
          class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-gray-200 transition-colors duration-200"
        >
          取消
        </button>
        <button
          @click="saveSettings"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm text-white transition-colors duration-200"
        >
          保存
        </button>
      </div>
    </div>
  </div>
</template>
