<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
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
  path: string
  thumbnail: string
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
const selectedGameType = ref('top-down-rpg')
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

const gameAssets = ref<GameAsset[]>([
  { id: 1, name: 'player.png', path: '/sprites/player.png', thumbnail: '🧙' },
  { id: 2, name: 'enemy_skeleton.png', path: '/sprites/enemy_skeleton.png', thumbnail: '💀' },
  { id: 3, name: 'gold_coin.png', path: '/sprites/gold_coin.png', thumbnail: '🪙' },
])

const entityProperties = ref<EntityProperty[]>([
  { name: '移动速度 (Speed)', value: 300, min: 0, max: 1000 },
  { name: '最大血量 (Health)', value: 100, min: 1, max: 500 },
])

const selectedEntity = ref('TestPlayer')
const isPlaying = ref(false)
const isGodotLaunched = ref(false)
const showGodotWarning = ref(false)
const godotWarningTimer = ref<number | null>(null)
const selectedComponents = ref<string[]>([])
const showSettingsModal = ref(false)
const godotExePath = ref(localStorage.getItem('godot_path') || '')

onMounted(async () => {
  try {
    const res = await fetch('http://localhost:8000/api/chat/history')
    const data = await res.json()
    if (data.status === 'success' && data.history && data.history.length > 0) {
      chatMessages.value = data.history.map((m: any, idx: number) => ({
        id: idx,
        role: m.role,
        content: m.content,
        timestamp: new Date()
      }))
    }
  } catch (e) {
    console.error('加载聊天历史失败:', e)
  }
})

const clearHistory = async () => {
  try {
    await fetch('http://localhost:8000/api/chat/clear', { method: 'POST' })
    chatMessages.value = [{
      id: 1,
      role: 'assistant',
      content: '你好！我是 AI Game Builder 助手。描述你想要创建的游戏角色或场景，我会帮你自动生成 Godot 实体配置。',
      timestamp: new Date()
    }]
  } catch (e) {
    console.error('清空聊天历史失败:', e)
  }
}

const gameTypes = [
  { id: 'top_down_rpg', name: '俯视角 RPG', icon: '🗡️' },
  { id: 'platformer', name: '横版跳跃', icon: '🏃' },
  { id: 'top_down_shooter', name: '俯视角射击', icon: '🔫' },
]

const llmModels = [
  { id: 'deepseek', name: 'DeepSeek' },
  { id: 'claude', name: 'Claude' },
  { id: 'ollama', name: '本地 Ollama' },
  { id: 'gpt4', name: 'GPT-4' },
]

const API_BASE_URL = 'http://localhost:8000'

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMsg: ChatMessage = {
    id: Date.now(),
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date()
  }
  chatMessages.value.push(userMsg)

  const userInput = inputMessage.value
  inputMessage.value = ''
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
        mode: currentMode.value,
        model_name: currentModel.value,
        api_key: apiKey.value || undefined,
        image_provider: selectedImageProvider.value,
        lora_model: customLora.value || undefined,
        art_api_key: artApiKey.value || undefined,
        art_base_url: artBaseUrl.value || undefined,
        game_base: selectedGameType.value,
        required_components: selectedComponents.value
      })
    })

    const result = await response.json()

    const loadingIndex = chatMessages.value.findIndex(m => m.id === loadingMsgId)
    if (loadingIndex !== -1) {
      if (response.ok && result.status === 'success') {
        chatMessages.value[loadingIndex] = {
          id: loadingMsgId,
          role: 'assistant',
          content: `✅ 实体 [${result.entity_name}] 装配成功！配置文件已送达引擎目录。\n\n📁 配置路径: ${result.config_path}`,
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

const saveSettings = () => {
  localStorage.setItem('godot_path', godotExePath.value)
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
        v-model:currentModel="currentModel"
        v-model:apiKey="apiKey"
        v-model:inputMessage="inputMessage"
        v-model:selectedGameType="selectedGameType"
        v-model:selectedComponents="selectedComponents"
        v-model:currentMode="currentMode"
        :chatMessages="chatMessages"
        :isLoading="isLoading"
        :gameTypes="gameTypes"
        :llmModels="llmModels"
        @send="sendMessageWithCheck"
      />
    </aside>

    <!-- 中间主屏：可视化舞台 -->
    <main class="flex-1 flex flex-col bg-slate-950">
      <GameStage
        :isPlaying="isPlaying"
        :isGodotLaunched="isGodotLaunched"
        @toggle-play="togglePlay"
        @launch-godot="launchGodot"
      />
    </main>

    <!-- 右侧边栏：资产与属性工厂 -->
    <aside class="w-1/4 min-w-[320px] flex flex-col bg-slate-900 border-l border-slate-700">
      <AssetPanel
        :assets="gameAssets"
        :entityProperties="entityProperties"
        :selectedEntity="selectedEntity"
        :selectedImageProvider="selectedImageProvider"
        :customLora="customLora"
        :imageProviders="imageProviders"
        :artApiKey="artApiKey"
        :artBaseUrl="artBaseUrl"
        :isTesting="isTesting"
        :testStatus="testStatus"
        @update-property="handlePropertyChange"
        @update:selectedImageProvider="selectedImageProvider = $event"
        @update:customLora="customLora = $event"
        @update:artApiKey="artApiKey = $event"
        @update:artBaseUrl="artBaseUrl = $event"
        @test-connection="testImageProvider"
      />
    </aside>
  </div>
  
  <!-- 设置按钮 -->
  <button
    @click="showSettingsModal = true"
    class="fixed bottom-4 right-4 w-12 h-12 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center shadow-lg border border-slate-600 transition-colors duration-200"
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
