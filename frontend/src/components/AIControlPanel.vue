<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import EntityWorkshop from './EntityWorkshop.vue'

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

interface SelectedSprite {
  name: string
  url: string
}

interface SceneEntitySnapshot {
  name: string
  components?: Record<string, Record<string, any>>
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
  selectedEntity: string
  selectedEntitySnapshot: SceneEntitySnapshot | null
  currentSelectedSprite: SelectedSprite | null
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
  (e: 'save-api-key', value: string): void
  (e: 'generate-entity', payload: { prompt: string; entityName: string; directAssembly: boolean; spriteName?: string }): void
  (e: 'quick-dialogue-update', dialogueText: string): void
}>()

const modes = [
  { id: 'chat', name: '💡 创意助理', placeholder: '向 AI 询问设定、构思剧情或数值规划...' },
  { id: 'build', name: '🛠️ 实体工坊', placeholder: '描述你想构建或修改的游戏实体...' },
  { id: 'art', name: '🎨 美术中心', placeholder: '描述你想生成的美术资产或图标...' }
]

const messagesContainer = ref<HTMLElement | null>(null)
const configSaveStatus = ref('')
const quickDialogueText = ref('')

watch(() => props.chatMessages.length, () => {
  setTimeout(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }, 50)
})

watch(() => props.currentMode, () => {
  setTimeout(() => {
    const input = document.querySelector('.chat-input') as HTMLInputElement
    if (input) input.focus()
  }, 100)
})

const currentPlaceholder = computed(() => {
  const mode = modes.find(m => m.id === props.currentMode)
  return mode?.placeholder || '描述你想要的游戏内容...'
})
const isBuildMode = computed(() => props.currentMode === 'build')
const isChatMode = computed(() => props.currentMode === 'chat')
const isArtMode = computed(() => props.currentMode === 'art')

// 游戏底座组件配置表
const genreComponents = {
  'top_down_rpg': [
    { id: 'PlayerInputComponent', name: '玩家输入移动', desc: '基于输入轴控制角色移动' },
    { id: 'HealthComponent', name: '生命管理', desc: '血量和死亡状态管理' },
    { id: 'InventoryComponent', name: '基础背包', desc: '维护道具与数量' }
  ],
  'platformer': [
    { id: 'PlayerInputComponent', name: '玩家输入移动', desc: '左右移动输入控制' },
    { id: 'GravityComponent', name: '重力与跳跃', desc: '处理重力、跳跃和坠落速度' },
    { id: 'HealthComponent', name: '生命管理', desc: '基础血量系统' }
  ],
  'top_down_shooter': [
    { id: 'PlayerInputComponent', name: '玩家输入移动', desc: '移动与走位控制' },
    { id: 'ProjectileShooterComponent', name: '弹幕发射', desc: '可手动或自动发射投射物' },
    { id: 'DetectionRangeComponent', name: '目标检测', desc: '检测敌人进入视野' }
  ],
  'tower_defense': [
    { id: 'DetectionRangeComponent', name: '范围检测', desc: '锁定进入射程的敌人' },
    { id: 'ProjectileShooterComponent', name: '塔台发射器', desc: '按射速发射子弹' },
    { id: 'GameStateFlagComponent', name: '关卡旗标', desc: '记录波次和胜负状态' }
  ],
  'roguelike': [
    { id: 'PlayerInputComponent', name: '玩家输入移动', desc: '角色探索控制' },
    { id: 'HealthComponent', name: '生命管理', desc: '基础生存能力' },
    { id: 'InventoryComponent', name: '物品管理', desc: '管理战利品与道具' }
  ],
  'survival': [
    { id: 'PlayerInputComponent', name: '生存移动', desc: '角色移动与规避' },
    { id: 'HealthComponent', name: '生命系统', desc: '管理伤害与恢复' },
    { id: 'CollectibleComponent', name: '资源拾取', desc: '采集并存入背包' }
  ],
  'strategy': [
    { id: 'PathFollowComponent', name: '路径行进', desc: '单位沿路径行进' },
    { id: 'GameStateFlagComponent', name: '策略变量', desc: '记录全局策略状态' },
    { id: 'DetectionRangeComponent', name: '侦察范围', desc: '识别附近单位' }
  ],
  'galgame_avg': [
    { id: 'DialoguePlayerComponent', name: '对话播放器', desc: '支持打字机效果的对话系统' },
    { id: 'GameStateFlagComponent', name: '剧情旗标', desc: '记录分支变量与进度' },
    { id: 'CharacterVisualComponent', name: '角色立绘', desc: '切换表情与立绘状态' }
  ],
}

// 当前底座的可用组件
const currentComponents = computed(() => {
  return genreComponents[props.selectedGameType as keyof typeof genreComponents] || []
})
const isGalgameMode = computed(() => props.selectedGameType === 'galgame_avg')

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}

const updateModelApiKey = (value: string) => {
  const models = [...props.llmModels]
  const idx = models.findIndex(m => m.id === props.currentModel)
  if (idx !== -1) {
    models[idx].api_key = value
    emit('update:apiKey', value)
    emit('update:newModelForm', { ...props.newModelForm, api_key: value })
    localStorage.setItem('llm_models', JSON.stringify(models))
  }
}

const saveCurrentApiKey = () => {
  const value = (props.llmModels?.find?.(m => m.id === props.currentModel)?.api_key || '').trim()
  configSaveStatus.value = value ? '正在保存...' : ''
  emit('save-api-key', value)
  if (value) {
    window.setTimeout(() => {
      configSaveStatus.value = '保存成功'
    }, 350)
    window.setTimeout(() => {
      configSaveStatus.value = ''
    }, 1800)
  }
}

const submitQuickDialogueUpdate = () => {
  const text = quickDialogueText.value.trim()
  if (!text) return
  emit('quick-dialogue-update', text)
}

watch(
  () => props.selectedGameType,
  () => {
    emit('update:selectedComponents', currentComponents.value.map(component => component.id))
  }
)
</script>

<template>
  <div class="flex flex-col h-full min-h-0 overflow-y-auto custom-scrollbar">
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
      <div v-if="currentModel !== 'ollama'" class="mb-3">
        <label class="block text-xs text-slate-400 mb-1">API Key</label>
        <div class="flex gap-2">
          <input
            type="password"
            :value="llmModels?.find?.(m => m.id === currentModel)?.api_key || ''"
            @input="updateModelApiKey(($event.target as HTMLInputElement).value)"
            @blur="saveCurrentApiKey"
            placeholder="sk-xxxxxxxxxxxxxxxx"
            class="flex-1 bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <button
            @click="saveCurrentApiKey"
            class="px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded text-white text-sm"
          >
            保存
          </button>
        </div>
        <div v-if="configSaveStatus" class="mt-1 text-xs text-emerald-300">{{ configSaveStatus }}</div>
      </div>
      
      <!-- Base URL (如果有) -->
      <div v-if="llmModels?.find?.(m => m.id === currentModel)?.base_url" class="mb-3">
        <label class="block text-xs text-slate-400 mb-1">API Base URL</label>
        <input
          type="text"
          :value="llmModels?.find?.(m => m.id === currentModel)?.base_url || ''"
          readonly
          class="w-full bg-slate-800/50 border border-slate-700 rounded px-3 py-2 text-sm text-slate-400"
        />
      </div>
      
      <!-- 未配置警告 -->
      <div v-if="!isModelConfigured" class="mb-3 p-2 bg-amber-900/30 border border-amber-700 rounded text-xs text-amber-200">
        ⚠️ 请配置 API Key 后再发送消息
      </div>
    </div>

    <div class="px-2 py-2 border-b border-slate-700 bg-slate-800/30 flex gap-1 shrink-0">
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

    <!-- 中部：游戏底座选择器 -->
    <div class="p-4 border-b border-slate-700">
      <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-3 font-semibold">
        游戏底座
      </h3>
      <div class="grid grid-cols-4 gap-2">
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
    
    <EntityWorkshop
      v-if="isBuildMode"
      :selectedGameType="selectedGameType"
      :selectedComponents="selectedComponents"
      :currentComponents="currentComponents"
      :selectedEntity="selectedEntity"
      :selectedEntitySnapshot="selectedEntitySnapshot"
      :currentSelectedSprite="currentSelectedSprite"
      :isLoading="isLoading"
      @update:selectedComponents="emit('update:selectedComponents', $event)"
      @generate-entity="emit('generate-entity', $event)"
    />

    <div v-if="isChatMode" class="p-4 border-b border-slate-700 bg-slate-900/50">
      <div class="rounded-lg border border-cyan-900/60 bg-slate-900/70 p-3">
        <div class="text-xs font-semibold text-cyan-300 mb-1">创意助理模块已启用</div>
        <div class="text-xs text-slate-400 leading-5">
          可直接讨论剧情设定、玩法规则、世界观结构与数值平衡，结果会保留在下方对话流中。
        </div>
      </div>
    </div>

    <div v-if="isArtMode" class="p-4 border-b border-slate-700 bg-slate-900/50">
      <div class="rounded-lg border border-violet-900/60 bg-slate-900/70 p-3">
        <div class="text-xs font-semibold text-violet-300 mb-1">美术中心模块已启用</div>
        <div class="text-xs text-slate-400 leading-5">
          在输入框描述画面后可直接生成素材；右侧素材库会显示并可一键点选用于实体装配。
        </div>
      </div>
    </div>

    <!-- 底部：对话流区域 -->
    <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
      <!-- 消息列表 -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        <template v-for="msg in chatMessages" :key="msg.id">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[85%] rounded-lg px-4 py-2 text-sm bg-blue-600 text-white">
              <div class="whitespace-pre-wrap">{{ msg.content }}</div>
              <div class="text-xs mt-1 text-blue-200">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>
          
          <!-- AI 回复 - 根据模式区分显示 -->
          <div v-else class="flex justify-start">
            <!-- Chat 模式：纯文本气泡 -->
            <div v-if="currentMode === 'chat' || !msg.content?.includes('entity_name')" 
                 class="max-w-[85%] rounded-lg px-4 py-2 text-sm bg-slate-800 text-gray-200">
              <div class="whitespace-pre-wrap">{{ msg.content }}</div>
              <div class="text-xs mt-1 text-slate-500">{{ formatTime(msg.timestamp) }}</div>
            </div>
            <!-- Build 模式：实体装配成功提示 -->
            <div v-else-if="currentMode === 'build' && msg.content?.includes('entity_name')" 
                 class="max-w-[85%] rounded-lg px-4 py-3 text-sm bg-emerald-900/50 border border-emerald-600 text-emerald-200">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-lg">✅</span>
                <span class="font-medium">实体装配成功</span>
              </div>
              <div class="text-xs text-emerald-300/70">{{ msg.content }}</div>
              <div class="text-xs mt-1 text-emerald-400/50">{{ formatTime(msg.timestamp) }}</div>
            </div>
            <!-- Art 模式 -->
            <div v-else 
                 class="max-w-[85%] rounded-lg px-4 py-2 text-sm bg-purple-900/50 border border-purple-600 text-purple-200">
              <div class="whitespace-pre-wrap">{{ msg.content }}</div>
              <div class="text-xs mt-1 text-purple-300/70">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>
        </template>
        
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
        <div v-if="currentMode === 'chat' && isGalgameMode" class="mb-3 p-3 rounded-lg border border-pink-700/50 bg-pink-900/20">
          <div class="text-xs uppercase tracking-wider text-pink-300 mb-2 font-semibold">Galgame 对话快捷输入</div>
          <textarea
            v-model="quickDialogueText"
            rows="4"
            placeholder="每行一条对白，例如：\n你终于来了。\n今天的风有点冷。"
            class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-pink-500"
          />
          <button
            @click="submitQuickDialogueUpdate"
            :disabled="isLoading || !quickDialogueText.trim()"
            class="mt-2 w-full py-2 bg-pink-700 hover:bg-pink-600 disabled:bg-slate-700 rounded text-sm text-white transition-colors"
          >
            一键更新对白到实体
          </button>
        </div>
        <div class="flex gap-2">
          <input
            type="text"
            :value="inputMessage"
            @input="emit('update:inputMessage', ($event.target as HTMLInputElement).value)"
            @keydown="handleKeydown"
            :placeholder="isModelConfigured ? currentPlaceholder : '请先在上方配置模型与 API Key...'"
            :disabled="isLoading"
            class="chat-input flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            @click="emit('send')"
            :disabled="isLoading || !inputMessage.trim() || !isModelConfigured"
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
