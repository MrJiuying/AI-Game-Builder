<script setup lang="ts">
import { ref, computed } from 'vue'

interface GameAsset {
  id: number
  name: string
  url: string
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

interface SceneEntity {
  name?: string
  components?: Record<string, Record<string, string | number | boolean | null>>
}

const props = defineProps<{
  assets: GameAsset[]
  abilityComponents: string[]
  entityProperties: EntityProperty[]
  selectedEntity: string
  selectedImageProvider: string
  customLora: string
  imageProviders: ImageProvider[]
  artApiKey: string
  artBaseUrl: string
  sceneState: Record<string, any>
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
const assetBrowserTab = ref<'sprites' | 'components'>('sprites')
const showLoraConfig = ref(false)
const loraModel = ref('none')

const loraOptions = [
  { id: 'none', name: '无' },
  { id: 'anime', name: '动漫风格' },
  { id: 'realistic', name: '写实风格' },
  { id: 'pixel', name: '像素风格' },
]

const sceneEntities = computed<SceneEntity[]>(() => {
  if (!props.sceneState || typeof props.sceneState !== 'object') return []
  const entities = props.sceneState.entities
  if (!Array.isArray(entities)) return []
  return entities
})

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
      <div class="p-4 border-b border-slate-700 bg-slate-900/60">
        <div class="flex gap-2">
          <button
            @click="assetBrowserTab = 'sprites'"
            :class="[
              'flex-1 px-3 py-2 rounded text-xs font-medium transition-all duration-200',
              assetBrowserTab === 'sprites'
                ? 'bg-cyan-900/60 text-cyan-300 border border-cyan-700'
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:text-slate-200'
            ]"
          >
            🎨 美术图库
          </button>
          <button
            @click="assetBrowserTab = 'components'"
            :class="[
              'flex-1 px-3 py-2 rounded text-xs font-medium transition-all duration-200',
              assetBrowserTab === 'components'
                ? 'bg-cyan-900/60 text-cyan-300 border border-cyan-700'
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:text-slate-200'
            ]"
          >
            🧩 能力芯片
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4">
        <div v-if="assetBrowserTab === 'sprites'" class="grid grid-cols-2 gap-3">
          <div
            v-for="asset in assets"
            :key="asset.id"
            class="rounded-lg border border-slate-700 bg-slate-800/70 overflow-hidden hover:border-cyan-700 transition-colors"
          >
            <div class="aspect-square bg-slate-900">
              <img :src="asset.url" :alt="asset.name" class="w-full h-full object-contain" />
            </div>
            <div class="px-2 py-1.5 text-[11px] text-slate-300 truncate">{{ asset.name }}</div>
          </div>
          <div v-if="assets.length === 0" class="col-span-2 text-xs text-slate-500">
            暂无可用贴图资源
          </div>
        </div>

        <div v-else class="flex flex-wrap gap-2">
          <div
            v-for="comp in abilityComponents"
            :key="comp"
            class="px-2.5 py-1 rounded-full text-xs border border-blue-700 bg-blue-900/30 text-blue-200"
          >
            {{ comp }}
          </div>
          <div v-if="abilityComponents.length === 0" class="text-xs text-slate-500">
            暂无能力芯片
          </div>
        </div>
      </div>
    </div>

    <!-- 属性检查器 -->
    <div v-if="activeTab === 'inspector'" class="flex-1 flex flex-col min-h-0 overflow-y-auto">
      <div class="p-4 border-b border-slate-700 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900">
        <div class="text-xs uppercase tracking-wider text-cyan-400 font-semibold mb-2">实时属性监控</div>
        <div class="text-xs text-slate-400">每 1.5 秒同步 Godot 场景状态</div>
      </div>

      <div class="p-4 space-y-4">
        <div v-if="sceneEntities.length === 0" class="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
          <div class="text-sm text-slate-300">暂无实时场景数据</div>
          <div class="text-xs text-slate-500 mt-1">等待 Godot 通过 WebSocket 推送 sync_state</div>
        </div>

        <div
          v-for="(entity, entityIndex) in sceneEntities"
          :key="`${entity.name || 'entity'}-${entityIndex}`"
          class="rounded-xl border border-cyan-900/60 bg-slate-900/80 shadow-[0_0_24px_rgba(34,211,238,0.08)]"
        >
          <div class="px-4 py-3 border-b border-cyan-900/40 flex items-center justify-between">
            <div class="text-cyan-300 font-semibold text-sm">{{ entity.name || `Entity_${entityIndex + 1}` }}</div>
            <div class="text-[11px] text-slate-500">Inspector Live</div>
          </div>

          <div class="p-3 space-y-3">
            <div
              v-for="(params, componentName) in (entity.components || {})"
              :key="componentName"
              class="rounded-lg border border-slate-700 bg-slate-800/70"
            >
              <div class="px-3 py-2 border-b border-slate-700 text-xs font-semibold text-blue-300">
                {{ componentName }}
              </div>
              <div class="p-3 grid grid-cols-2 gap-2">
                <div
                  v-for="(paramValue, paramKey) in params"
                  :key="`${componentName}-${paramKey}`"
                  class="rounded bg-slate-900/80 border border-slate-700 px-2 py-1.5"
                >
                  <div class="text-[11px] text-slate-500">{{ paramKey }}</div>
                  <div class="text-xs text-slate-100 font-medium break-all">{{ paramValue }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
