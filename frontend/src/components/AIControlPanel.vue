<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface GameType {
  id: string
  name: string
  icon: string
}

interface LLMModel {
  id: string
  name: string
}

interface Component {
  id: string
  name: string
  desc: string
}

const props = defineProps<{
  currentModel: string
  apiKey: string
  inputMessage: string
  selectedGameType: string
  chatMessages: ChatMessage[]
  isLoading: boolean
  gameTypes: GameType[]
  llmModels: { id: string; name: string; api_key: string; base_url: string }[]
  selectedComponents: string[]
  currentMode: string
  isModelConfigured: boolean
  showAddModelModal: boolean
  newModelForm: { id: string; name: string; api_key: string; base_url: string }
}>()

const emit = defineEmits<{
  (e: 'update:currentModel', value: string): void
  (e: 'update:apiKey', value: string): void
  (e: 'update:inputMessage', value: string): void
  (e: 'update:selectedGameType', value: string): void
  (e: 'update:selectedComponents', value: string[]): void
  (e: 'update:currentMode', value: string): void
  (e: 'update:showAddModelModal', value: boolean): void
  (e: 'update:newModelForm', value: { id: string; name: string; api_key: string; base_url: string }): void
  (e: 'addModel'): void
  (e: 'send'): void
}>()

const modes = [
  { id: 'chat', name: '💡 创意助理', placeholder: '向 AI 询问设定、构思剧情或数值规划...' },
  { id: 'build', name: '🛠️ 实体工坊', placeholder: '描述你想构建或修改的游戏实体...' },
  { id: 'art', name: '🎨 美术中心', placeholder: '描述你想生成的美术资产或图标...' }
]

const currentPlaceholder = computed(() => {
  const mode = modes.find(m => m.id === props.currentMode)
  return mode?.placeholder || '描述你想要的游戏内容...'
})

// 游戏底座组件配置表
const genreComponents = {
  'top_down_rpg': [
    { id: 'TopDownMovementComponent', name: '八向平滑移动', desc: '包含加速度与摩擦力的物理移动' },
    { id: 'CollisionGeneratorComponent', name: '动态物理碰撞箱', desc: '自动生成圆形/矩形碰撞体积' }
  ],
  'platformer': [
    { id: 'PlatformerMovementComponent', name: '重力跳跃移动', desc: '横版专属重力与跳跃控制' }
  ],
  'top_down_shooter': [
    { id: 'AimingComponent', name: '精确瞄准', desc: '通过鼠标或摇杆精确瞄准' },
    { id: 'ProjectileEmitterComponent', name: '子弹发射', desc: '发射实体子弹或能量球' }
  ]
}

// 当前底座的可用组件
const currentComponents = computed(() => {
  return genreComponents[props.selectedGameType as keyof typeof genreComponents] || []
})

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}

const toggleComponent = (componentId: string) => {
  const current = [...props.selectedComponents]
  const index = current.indexOf(componentId)
  
  if (index > -1) {
    current.splice(index, 1)
  } else {
    current.push(componentId)
  }
  
  emit('update:selectedComponents', current)
}

const updateModelApiKey = (value: string) => {
  const models = [...props.llmModels]
  const idx = models.findIndex(m => m.id === props.currentModel)
  if (idx !== -1) {
    models[idx].api_key = value
    emit('update:newModelForm', { ...props.newModelForm, api_key: value })
    localStorage.setItem('llm_models', JSON.stringify(models))
  }
}

// 监听游戏底座变化，清空选中的组件
watch(
  () => props.selectedGameType,
  () => {
    emit('update:selectedComponents', [])
  }
)
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 顶部：大模型设置区 -->
    <div class="p-4 border-b border-slate-700 bg-slate-800/50">
      <h2 class="text-xs uppercase tracking-wider text-slate-400 mb-3 font-semibold">
        AI 核心控制舱
      </h2>
      
      <!-- 模型选择 -->
      <div class="mb-3 flex gap-2">
        <div class="flex-1">
          <label class="block text-xs text-slate-400 mb-1">选择模型</label>
          <select
            :value="currentModel"
            @change="emit('update:currentModel', ($event.target as HTMLSelectElement).value)"
            class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          >
            <option v-for="model in llmModels" :key="model.id" :value="model.id">
              {{ model.name }}
            </option>
          </select>
        </div>
        <button
          @click="emit('update:showAddModelModal', true)"
          class="self-end px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded text-gray-200 text-sm"
          title="添加模型"
        >
          ➕
        </button>
      </div>
      
      <!-- API Key (按模型显示) -->
      <div v-if="llmModels.find(m => m.id === currentModel)?.id !== 'ollama'" class="mb-3">
        <label class="block text-xs text-slate-400 mb-1">API Key</label>
        <input
          type="password"
          :value="llmModels.find(m => m.id === currentModel)?.api_key || ''"
          @input="updateModelApiKey(($event.target as HTMLInputElement).value)"
          placeholder="sk-xxxxxxxxxxxxxxxx"
          class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>
      
      <!-- Base URL (如果有) -->
      <div v-if="llmModels.find(m => m.id === currentModel)?.base_url" class="mb-3">
        <label class="block text-xs text-slate-400 mb-1">API Base URL</label>
        <input
          type="text"
          :value="llmModels.find(m => m.id === currentModel)?.base_url || ''"
          readonly
          class="w-full bg-slate-800/50 border border-slate-700 rounded px-3 py-2 text-sm text-slate-400"
        />
      </div>
      
      <!-- 未配置警告 -->
      <div v-if="!isModelConfigured" class="mb-3 p-2 bg-amber-900/30 border border-amber-700 rounded text-xs text-amber-200">
        ⚠️ 请配置 API Key 后再发送消息
      </div>
    </div>

    <!-- 中部：游戏底座选择器 -->
    <div class="p-4 border-b border-slate-700">
      <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-3 font-semibold">
        游戏底座
      </h3>
      <div class="grid grid-cols-3 gap-2">
        <button
          v-for="gameType in gameTypes"
          :key="gameType.id"
          @click="emit('update:selectedGameType', gameType.id)"
          :class="[
            'p-2 rounded text-center transition-all duration-200 text-xs',
            selectedGameType === gameType.id
              ? 'bg-blue-600 text-white'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          ]"
        >
          <div class="text-lg mb-1">{{ gameType.icon }}</div>
          <div>{{ gameType.name }}</div>
        </button>
      </div>
    </div>
    
    <!-- 可选能力蓝图 -->
    <div class="p-4 border-b border-slate-700">
      <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-3 font-semibold">
        可选能力蓝图 (Available Abilities)
      </h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="component in currentComponents"
          :key="component.id"
          @click="toggleComponent(component.id)"
          :title="component.desc"
          :class="[
            'px-3 py-1.5 rounded-full text-xs transition-all duration-200',
            selectedComponents.includes(component.id)
              ? 'bg-blue-600 text-white border border-blue-400 shadow-sm'
              : 'bg-slate-800 text-slate-300 border border-slate-600 hover:bg-slate-700'
          ]"
        >
          {{ component.name }}
        </button>
        <div v-if="currentComponents.length === 0" class="text-xs text-slate-500">
          暂无可用能力
        </div>
      </div>
    </div>

    <!-- 底部：对话流区域 -->
    <div class="flex-1 flex flex-col min-h-0">
      <!-- 模式切换 Tab -->
      <div class="px-2 py-2 border-b border-slate-700 bg-slate-800/30 flex gap-1">
        <button
          v-for="mode in modes"
          :key="mode.id"
          @click="emit('update:currentMode', mode.id)"
          :class="[
            'flex-1 py-1.5 px-2 rounded text-xs font-medium transition-all duration-200',
            currentMode === mode.id
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-300'
          ]"
        >
          {{ mode.name }}
        </button>
      </div>
      
      <!-- 消息列表 -->
      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <div
          v-for="msg in chatMessages"
          :key="msg.id"
          :class="[
            'flex',
            msg.role === 'user' ? 'justify-end' : 'justify-start'
          ]"
        >
          <div
            :class="[
              'max-w-[85%] rounded-lg px-4 py-2 text-sm',
              msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-gray-200'
            ]"
          >
            <div class="whitespace-pre-wrap">{{ msg.content }}</div>
            <div :class="['text-xs mt-1', msg.role === 'user' ? 'text-blue-200' : 'text-slate-500']">
              {{ formatTime(msg.timestamp) }}
            </div>
          </div>
        </div>
        
        <!-- 加载状态 -->
        <div v-if="isLoading" class="flex justify-start">
          <div class="bg-slate-800 rounded-lg px-4 py-3">
            <div class="flex space-x-1">
              <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
              <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
              <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="p-4 border-t border-slate-700 bg-slate-800/50">
        <div class="flex gap-2">
          <input
            type="text"
            :value="inputMessage"
            @input="emit('update:inputMessage', ($event.target as HTMLInputElement).value)"
            @keydown="handleKeydown"
            :placeholder="currentPlaceholder"
            :disabled="isLoading"
            class="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            @click="emit('send')"
            :disabled="isLoading || !inputMessage.trim()"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-lg transition-colors duration-200"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 添加模型弹窗 -->
      <div v-if="showAddModelModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="emit('update:showAddModelModal', false)"></div>
        <div class="relative bg-slate-800 rounded-xl shadow-2xl border border-slate-700 w-full max-w-md p-6">
          <h3 class="text-lg font-bold text-gray-200 mb-4">添加自定义模型</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-xs text-slate-400 mb-1">模型标识 (ID)</label>
              <input
                v-model="newModelForm.id"
                placeholder="如: my-gpt4"
                class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">显示名称</label>
              <input
                v-model="newModelForm.name"
                placeholder="如: My GPT-4"
                class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">API Key</label>
              <input
                v-model="newModelForm.api_key"
                placeholder="sk-..."
                type="password"
                class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200"
              />
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Base URL (可选)</label>
              <input
                v-model="newModelForm.base_url"
                placeholder="如: https://api.openai.com/v1"
                class="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200"
              />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button
              @click="emit('update:showAddModelModal', false)"
              class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-gray-200"
            >
              取消
            </button>
            <button
              @click="emit('addModel'); emit('update:showAddModelModal', false)"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white"
            >
              添加
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
