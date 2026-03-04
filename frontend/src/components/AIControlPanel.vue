<script setup lang="ts">
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

const props = defineProps<{
  currentModel: string
  apiKey: string
  inputMessage: string
  selectedGameType: string
  chatMessages: ChatMessage[]
  isLoading: boolean
  gameTypes: GameType[]
  llmModels: LLMModel[]
}>()

const emit = defineEmits<{
  (e: 'update:currentModel', value: string): void
  (e: 'update:apiKey', value: string): void
  (e: 'update:inputMessage', value: string): void
  (e: 'update:selectedGameType', value: string): void
  (e: 'send'): void
}>()

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 顶部：大模型设置区 -->
    <div class="p-4 border-b border-slate-700 bg-slate-800/50">
      <h2 class="text-xs uppercase tracking-wider text-slate-400 mb-3 font-semibold">
        AI 核心控制舱
      </h2>
      
      <!-- 模型选择 -->
      <div class="mb-3">
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
      
      <!-- API Key -->
      <div>
        <label class="block text-xs text-slate-400 mb-1">API Key</label>
        <input
          type="password"
          :value="apiKey"
          @input="emit('update:apiKey', ($event.target as HTMLInputElement).value)"
          placeholder="sk-xxxxxxxxxxxxxxxx"
          class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
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

    <!-- 底部：对话流区域 -->
    <div class="flex-1 flex flex-col min-h-0">
      <div class="px-4 py-2 border-b border-slate-700 bg-slate-800/30">
        <h3 class="text-xs uppercase tracking-wider text-slate-400 font-semibold">
          对话流
        </h3>
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
            placeholder="描述你想要的游戏内容..."
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
    </div>
  </div>
</template>
