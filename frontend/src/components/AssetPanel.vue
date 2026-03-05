<script setup lang="ts">
import { ref } from 'vue'

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

interface ImageProvider {
  id: string
  name: string
}

const props = defineProps<{
  assets: GameAsset[]
  entityProperties: EntityProperty[]
  selectedEntity: string
  selectedImageProvider: string
  customLora: string
  imageProviders: ImageProvider[]
  artApiKey: string
  artBaseUrl: string
  isTesting: boolean
  testStatus: { status: 'idle' | 'success' | 'error'; message: string }
}>()

const emit = defineEmits<{
  (e: 'update-property', propertyName: string, value: number): void
  (e: 'update:selectedImageProvider', value: string): void
  (e: 'update:customLora', value: string): void
  (e: 'update:artApiKey', value: string): void
  (e: 'update:artBaseUrl', value: string): void
  (e: 'test-connection'): void
}>()

const activeTab = ref<'assets' | 'inspector'>('assets')
const showLoraConfig = ref(false)
const loraModel = ref('none')

const loraOptions = [
  { id: 'none', name: '无' },
  { id: 'anime', name: '动漫风格' },
  { id: 'realistic', name: '写实风格' },
  { id: 'pixel', name: '像素风格' },
]

const handleSliderChange = (propertyName: string, event: Event) => {
  const value = parseFloat((event.target as HTMLInputElement).value)
  emit('update-property', propertyName, value)
}

const handleNumberChange = (propertyName: string, event: Event) => {
  const value = parseFloat((event.target as HTMLInputElement).value)
  if (!isNaN(value)) {
    emit('update-property', propertyName, value)
  }
}

const handleImageProviderChange = (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  emit('update:selectedImageProvider', value)
}

const handleLoraChange = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  emit('update:customLora', value)
}

const handleArtApiKeyChange = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  emit('update:artApiKey', value)
}

const handleArtBaseUrlChange = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  emit('update:artBaseUrl', value)
}

const handleTestConnection = () => {
  emit('test-connection')
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 标签切换 -->
    <div class="flex border-b border-slate-700">
      <button
        @click="activeTab = 'assets'"
        :class="[
          'flex-1 px-4 py-3 text-sm font-medium transition-colors duration-200',
          activeTab === 'assets'
            ? 'bg-slate-800 text-blue-400 border-b-2 border-blue-400'
            : 'text-slate-400 hover:text-gray-200 hover:bg-slate-800/50'
        ]"
      >
        美术资产库
      </button>
      <button
        @click="activeTab = 'inspector'"
        :class="[
          'flex-1 px-4 py-3 text-sm font-medium transition-colors duration-200',
          activeTab === 'inspector'
            ? 'bg-slate-800 text-blue-400 border-b-2 border-blue-400'
            : 'text-slate-400 hover:text-gray-200 hover:bg-slate-800/50'
        ]"
      >
        属性检查器
      </button>
    </div>

    <!-- 美术资产库 -->
    <div v-if="activeTab === 'assets'" class="flex-1 flex flex-col min-h-0">
      <!-- 美术引擎配置 -->
      <div class="p-4 border-b border-slate-700 bg-slate-800/30">
        <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-3 font-semibold">
          美术引擎配置 (Art Engine)
        </h3>
        
        <!-- 算力下拉框 -->
        <div class="mb-3">
          <label class="block text-xs text-slate-400 mb-1">算力选择</label>
          <select
            :value="selectedImageProvider"
            @change="handleImageProviderChange"
            class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          >
            <option v-for="provider in imageProviders" :key="provider.id" :value="provider.id">
              {{ provider.name }}
            </option>
          </select>
        </div>
        
        <!-- LoRA 挂载槽 -->
        <div>
          <label class="block text-xs text-slate-400 mb-1">LoRA 挂载槽</label>
          <input
            type="text"
            :value="customLora"
            @input="handleLoraChange"
            placeholder="输入专属 LoRA 名称或权重链接 (选填)"
            class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        
        <!-- 配置折叠面板 -->
        <div class="mt-4">
          <h4 class="text-xs text-slate-400 mb-2">引擎配置</h4>
          
          <!-- 本地 SD -->
          <div v-if="selectedImageProvider === 'local_sd'" class="bg-slate-800/50 border border-slate-700 rounded p-3">
            <p class="text-xs text-slate-500">本地 SD WebUI 不需要 API Key，请确保服务已启动。</p>
          </div>
          
          <!-- DALL-E 3 或 Cloud SD -->
          <div v-else class="space-y-3">
            <!-- 美术 API Key -->
            <div>
              <label class="block text-xs text-slate-400 mb-1">美术 API Key</label>
              <input
                type="password"
                :value="artApiKey"
                @input="handleArtApiKeyChange"
                placeholder="输入 API Key"
                class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            
            <!-- 接口地址 (仅 Cloud SD) -->
            <div v-if="selectedImageProvider === 'cloud_sd'">
              <label class="block text-xs text-slate-400 mb-1">接口地址 (Base URL)</label>
              <input
                type="text"
                :value="artBaseUrl"
                @input="handleArtBaseUrlChange"
                placeholder="https://api.example.com"
                class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
          
          <!-- 测试连接按钮 -->
          <div class="mt-4 flex items-center gap-2">
            <button
              @click="handleTestConnection"
              :disabled="isTesting"
              class="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded text-xs text-gray-300 transition-colors duration-200"
            >
              <span v-if="isTesting" class="animate-spin">⚡</span>
              <span v-else>⚡</span>
              测试连接
            </button>
            
            <!-- 测试状态反馈 -->
            <div v-if="testStatus.status === 'success'" class="text-xs text-green-400 flex items-center gap-1">
              ✅ 连接成功
            </div>
            <div v-else-if="testStatus.status === 'error'" class="text-xs text-red-400 flex items-center gap-1">
              ❌ 连接失败: {{ testStatus.message }}
            </div>
          </div>
        </div>
      </div>

      <!-- LORA 配置 -->
      <div class="p-4 border-b border-slate-700 bg-slate-800/30">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-slate-400">预设 LoRA 模型</span>
          <button
            @click="showLoraConfig = !showLoraConfig"
            class="text-xs text-blue-400 hover:text-blue-300"
          >
            {{ showLoraConfig ? '收起' : '配置' }}
          </button>
        </div>
        <select
          v-if="showLoraConfig"
          v-model="loraModel"
          class="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
        >
          <option v-for="opt in loraOptions" :key="opt.id" :value="opt.id">
            {{ opt.name }}
          </option>
        </select>
      </div>

      <!-- 上传按钮 -->
      <div class="p-4 border-b border-slate-700">
        <button class="w-full py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg text-sm text-gray-300 transition-colors duration-200 flex items-center justify-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
          上传本地素材
        </button>
      </div>

      <!-- 资产网格 -->
      <div class="flex-1 overflow-y-auto p-4">
        <div class="grid grid-cols-3 gap-2">
          <div
            v-for="asset in assets"
            :key="asset.id"
            class="aspect-square bg-slate-800 rounded-lg flex flex-col items-center justify-center cursor-pointer hover:bg-slate-700 transition-colors duration-200 group relative"
          >
            <div class="text-2xl">{{ asset.thumbnail }}</div>
            <div class="text-[10px] text-slate-400 mt-1 truncate w-full text-center px-1">
              {{ asset.name }}
            </div>
            <!-- 悬停显示删除按钮 -->
            <button class="absolute top-1 right-1 w-5 h-5 bg-red-600 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
          
          <!-- 添加更多占位 -->
          <div class="aspect-square bg-slate-800/50 rounded-lg border-2 border-dashed border-slate-700 flex flex-col items-center justify-center cursor-pointer hover:border-slate-500 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-slate-500" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- 属性检查器 -->
    <div v-if="activeTab === 'inspector'" class="flex-1 flex flex-col min-h-0 overflow-y-auto">
      <!-- 选中实体信息 -->
      <div class="p-4 border-b border-slate-700 bg-slate-800/30">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">
            {{ selectedEntity.charAt(0) }}
          </div>
          <div>
            <div class="text-sm font-medium text-gray-200">{{ selectedEntity }}</div>
            <div class="text-xs text-slate-500">CharacterBody2D</div>
          </div>
        </div>
      </div>

      <!-- 属性列表 -->
      <div class="p-4 space-y-4">
        <div v-for="prop in entityProperties" :key="prop.name" class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-xs text-slate-400">{{ prop.name }}</label>
            <input
              type="number"
              :value="prop.value"
              @change="handleNumberChange(prop.name, $event)"
              class="w-16 bg-slate-800 border border-slate-600 rounded px-2 py-0.5 text-xs text-gray-200 text-right focus:outline-none focus:border-blue-500"
            />
          </div>
          <div class="flex items-center gap-2">
            <input
              type="range"
              :min="prop.min"
              :max="prop.max"
              :value="prop.value"
              @input="handleSliderChange(prop.name, $event)"
              class="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <span class="text-xs text-slate-500 w-12 text-right">{{ prop.value }}</span>
          </div>
        </div>
        
        <!-- 额外示例属性 -->
        <div class="pt-4 border-t border-slate-700 space-y-4">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-xs text-slate-400">碰撞层 (Collision Layer)</label>
              <input
                type="number"
                value="1"
                class="w-16 bg-slate-800 border border-slate-600 rounded px-2 py-0.5 text-xs text-gray-200 text-right focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
          
          <div class="space-y-2">
            <label class="text-xs text-slate-400">颜色滤镜</label>
            <div class="flex gap-2">
              <div class="w-8 h-8 rounded bg-white cursor-pointer border-2 border-blue-500"></div>
              <div class="w-8 h-8 rounded bg-red-500 cursor-pointer border-2 border-transparent hover:border-slate-500"></div>
              <div class="w-8 h-8 rounded bg-green-500 cursor-pointer border-2 border-transparent hover:border-slate-500"></div>
              <div class="w-8 h-8 rounded bg-blue-500 cursor-pointer border-2 border-transparent hover:border-slate-500"></div>
              <button class="w-8 h-8 rounded bg-slate-700 border-2 border-dashed border-slate-500 flex items-center justify-center text-xs text-slate-400 hover:bg-slate-600">
                +
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
