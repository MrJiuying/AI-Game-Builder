<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  isPlaying: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-play'): void
}>()

const isPaused = ref(false)
const sceneName = ref('未命名场景')

const handlePause = () => {
  isPaused.value = !isPaused.value
}

const handleReset = () => {
  isPaused.value = false
  emit('toggle-play')
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 顶部场景信息栏 -->
    <div class="px-4 py-2 bg-slate-900 border-b border-slate-700 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-red-500"></div>
          <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div class="w-3 h-3 rounded-full bg-green-500"></div>
        </div>
        <span class="text-sm text-slate-400">{{ sceneName }}</span>
      </div>
      <div class="text-xs text-slate-500">60 FPS</div>
    </div>

    <!-- 主画布区域 -->
    <div class="flex-1 flex items-center justify-center p-4">
      <div class="w-full h-full bg-slate-900 border-2 border-dashed border-slate-700 rounded-lg flex flex-col items-center justify-center relative overflow-hidden">
        <!-- 背景网格 -->
        <div class="absolute inset-0 opacity-10" 
          style="background-image: linear-gradient(#475569 1px, transparent 1px), linear-gradient(90deg, #475569 1px, transparent 1px); background-size: 20px 20px;">
        </div>
        
        <!-- 占位文字 -->
        <div class="relative z-10 text-center">
          <div class="text-6xl mb-4">🎮</div>
          <h3 class="text-xl font-semibold text-slate-400 mb-2">Godot 实时渲染引擎挂载区</h3>
          <p class="text-sm text-slate-500">等待 AI 生成游戏内容...</p>
        </div>
        
        <!-- 模拟的游戏元素 -->
        <div class="absolute bottom-8 left-8 flex items-end gap-4">
          <div class="w-12 h-16 bg-blue-600 rounded-md flex items-center justify-center text-white text-xs font-bold shadow-lg">
            P
          </div>
          <div class="w-10 h-12 bg-red-600 rounded-md flex items-center justify-center text-white text-xs font-bold shadow-lg">
            E
          </div>
          <div class="w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center shadow-lg">
            💰
          </div>
        </div>
      </div>
    </div>

    <!-- 底部播放控制区 -->
    <div class="px-4 py-3 bg-slate-900 border-t border-slate-700 flex items-center justify-center gap-4">
      <!-- 重置按钮 -->
      <button
        @click="handleReset"
        class="w-10 h-10 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center transition-colors duration-200 group"
        title="重置"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-400 group-hover:text-white" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
        </svg>
      </button>

      <!-- 播放/暂停按钮 -->
      <button
        @click="emit('toggle-play')"
        :class="[
          'w-14 h-14 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg',
          isPlaying 
            ? 'bg-yellow-600 hover:bg-yellow-700' 
            : 'bg-green-600 hover:bg-green-700'
        ]"
        :title="isPlaying ? '暂停' : '运行'"
      >
        <svg v-if="!isPlaying" xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-white" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-white" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
      </button>

      <!-- 暂停按钮（独立） -->
      <button
        @click="handlePause"
        :disabled="!isPlaying"
        class="w-10 h-10 rounded-full bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition-colors duration-200 group"
        title="暂停"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-400 group-hover:text-white" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
  </div>
</template>
