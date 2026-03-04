<script setup lang="ts">
import { ref, computed } from 'vue'
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
const isLoading = ref(false)

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

const gameTypes = [
  { id: 'top-down-rpg', name: '俯视角 RPG', icon: '🗡️' },
  { id: 'platformer', name: '横版跳跃', icon: '🏃' },
  { id: 'top-down-shooter', name: '俯视角射击', icon: '🔫' },
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
  const loadingMsg: ChatMessage = {
    id: loadingMsgId,
    role: 'assistant',
    content: '⏳ 正在向神经中枢发送指令，调动 Godot 装配车间...',
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
        model_name: currentModel.value,
        api_key: apiKey.value || undefined
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
        chatMessages.value[loadingIndex] = {
          id: loadingMsgId,
          role: 'assistant',
          content: `❌ 生成失败: ${result.error || result.message || '未知错误'}`,
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

const togglePlay = () => {
  isPlaying.value = !isPlaying.value
}

const handlePropertyChange = (propertyName: string, newValue: number) => {
  const prop = entityProperties.value.find(p => p.name === propertyName)
  if (prop) {
    prop.value = newValue
  }
}
</script>

<template>
  <div class="h-screen w-screen flex bg-slate-950 text-gray-200 overflow-hidden">
    <!-- 左侧边栏：AI 核心控制舱 -->
    <aside class="w-1/4 min-w-[320px] flex flex-col bg-slate-900 border-r border-slate-700">
      <AIControlPanel
        v-model:currentModel="currentModel"
        v-model:apiKey="apiKey"
        v-model:inputMessage="inputMessage"
        v-model:selectedGameType="selectedGameType"
        :chatMessages="chatMessages"
        :isLoading="isLoading"
        :gameTypes="gameTypes"
        :llmModels="llmModels"
        @send="sendMessage"
      />
    </aside>

    <!-- 中间主屏：可视化舞台 -->
    <main class="flex-1 flex flex-col bg-slate-950">
      <GameStage
        :isPlaying="isPlaying"
        @toggle-play="togglePlay"
      />
    </main>

    <!-- 右侧边栏：资产与属性工厂 -->
    <aside class="w-1/4 min-w-[320px] flex flex-col bg-slate-900 border-l border-slate-700">
      <AssetPanel
        :assets="gameAssets"
        :entityProperties="entityProperties"
        :selectedEntity="selectedEntity"
        @update-property="handlePropertyChange"
      />
    </aside>
  </div>
</template>
