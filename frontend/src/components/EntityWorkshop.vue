<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface ComponentBlueprint {
  id: string
  name: string
  desc: string
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
  selectedGameType: string
  selectedComponents: string[]
  currentComponents: ComponentBlueprint[]
  selectedEntity: string
  selectedEntitySnapshot: SceneEntitySnapshot | null
  currentSelectedSprite: SelectedSprite | null
  isLoading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:selectedComponents', value: string[]): void
  (e: 'generate-entity', payload: { prompt: string; entityName: string; directAssembly: boolean; spriteName?: string }): void
}>()

const workshopPrompt = ref('')
const entityName = ref('')

const componentParamExamples: Record<string, Record<string, any>> = {
  PlayerInputComponent: { max_speed: 260, acceleration: 1400, friction: 1200 },
  GravityComponent: { gravity_scale: 1.0, jump_force: 360, max_fall_speed: 1200 },
  PathFollowComponent: { move_speed: 140, loop_path: true, arrive_distance: 10 },
  HealthComponent: { max_health: 100, current_health: 100, can_overheal: false },
  DamageOnTouchComponent: { damage: 10, cooldown: 0.2, enabled: true },
  ProjectileShooterComponent: { fire_rate: 0.25, projectile_speed: 500, damage: 10 },
  ChaseTargetComponent: { max_speed: 180, acceleration: 900, stopping_distance: 12 },
  PatrolComponent: { move_speed: 120, wait_time: 0.5, loop_patrol: true },
  DetectionRangeComponent: { detection_radius: 220, target_group: 'player', update_interval: 0.1 },
  AreaTriggerComponent: { trigger_group: 'player', once: false, cooldown: 0.0 },
  CollectibleComponent: { item_id: 'coin', amount: 1, auto_collect: true },
  ClickInteractComponent: { interact_distance: 120, once: false, enabled: true },
  ParallaxBackgroundComponent: { scroll_speed_x: 0.2, scroll_speed_y: 0.0 },
  CameraFollowComponent: { follow_smoothing: 8.0, offset_x: 0, offset_y: 0 },
  InventoryComponent: { max_slots: 24, stack_limit: 99, allow_new_items: true },
  GameStateFlagComponent: { namespace: 'global', use_global_store: true },
  AnimationStateComponent: { idle_state: 'idle', move_state: 'run', speed_scale: 1.0 },
  EffectPlayerComponent: { effect_name: 'hit', auto_play: false, cooldown: 0.15 },
  DialoguePlayerComponent: { typing_speed: 0.03, auto_hide_on_finish: true, enabled: true },
  CharacterVisualComponent: { portrait_key: 'hero_default', expression: 'neutral', visible: true },
}

const selectedComponentDefs = computed(() => {
  return props.currentComponents.filter(c => props.selectedComponents.includes(c.id))
})

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

const buildAutoPrompt = () => {
  const componentsText = props.selectedComponents.length > 0 ? props.selectedComponents.join('、') : '基础组件'
  const spriteHint = props.currentSelectedSprite ? `并使用贴图 ${props.currentSelectedSprite.name}` : '并选择默认贴图'
  return `基于 ${props.selectedGameType} 底座，生成一个新实体并挂载以下组件：${componentsText}，${spriteHint}。请给出合理参数。`
}

const generateEntity = () => {
  const prompt = workshopPrompt.value.trim() || buildAutoPrompt()
  const normalizedEntityName = entityName.value.trim() || 'VisualEntity'
  emit('generate-entity', {
    prompt,
    entityName: normalizedEntityName,
    directAssembly: !!props.currentSelectedSprite,
    spriteName: props.currentSelectedSprite?.name
  })
}

const prettyJson = (value: Record<string, any>) => JSON.stringify(value, null, 2)

watch(
  () => props.currentSelectedSprite,
  (sprite) => {
    if (!sprite) return
    const base = sprite.name.replace(/\.[^/.]+$/, '').trim()
    if (base) {
      entityName.value = base
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="p-4 border-b border-slate-700 bg-slate-900/50">
    <h3 class="text-xs uppercase tracking-wider text-cyan-400 mb-3 font-semibold">
      实体工坊 (Entity Workshop)
    </h3>

    <div class="mb-3 rounded-lg border border-cyan-900/60 bg-slate-900/70 overflow-hidden">
      <div class="px-3 py-2 text-xs font-semibold text-cyan-300 border-b border-slate-700">装配预览区 (Visual Assembly)</div>
      <div class="p-3">
        <div v-if="currentSelectedSprite" class="space-y-2">
          <div class="w-full h-32 rounded border border-slate-700 bg-slate-950 flex items-center justify-center overflow-hidden">
            <img :src="currentSelectedSprite.url" :alt="currentSelectedSprite.name" class="max-w-full max-h-full object-contain" />
          </div>
          <div class="text-[11px] text-cyan-200 break-all">{{ currentSelectedSprite.name }}</div>
        </div>
        <div v-else class="text-xs text-slate-500">尚未选择美术素材，请在右侧素材库点选一张贴图。</div>
      </div>
    </div>

    <div class="mb-3">
      <label class="block text-xs text-slate-400 mb-1">实体名称</label>
      <input
        v-model="entityName"
        type="text"
        placeholder="选中贴图后会自动填入文件名"
        class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
      />
    </div>

    <div class="mb-3 rounded-lg border border-slate-700 bg-slate-900/70 overflow-hidden">
      <div class="px-3 py-2 text-xs font-semibold text-violet-300 border-b border-slate-700">
        当前选中实体：{{ selectedEntity || '未选择' }}
      </div>
      <div class="p-3">
        <div v-if="selectedEntitySnapshot && selectedEntitySnapshot.components" class="space-y-2">
          <div
            v-for="(params, compName) in selectedEntitySnapshot.components"
            :key="compName"
            class="rounded border border-slate-700 bg-slate-800/70 p-2"
          >
            <div class="text-[11px] text-violet-300 font-semibold mb-1">{{ compName }}</div>
            <div class="grid grid-cols-2 gap-1">
              <div
                v-for="(paramValue, paramKey) in params"
                :key="`${compName}-${paramKey}`"
                class="rounded bg-slate-900/70 border border-slate-700 px-2 py-1"
              >
                <div class="text-[10px] text-slate-500">{{ paramKey }}</div>
                <div class="text-[11px] text-slate-200 break-all">{{ paramValue }}</div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-xs text-slate-500">尚未从实时场景同步到该实体属性。</div>
      </div>
    </div>

    <div class="space-y-2 mb-3">
      <div class="text-xs text-slate-400">推荐组件勾选</div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="component in currentComponents"
          :key="component.id"
          @click="toggleComponent(component.id)"
          :title="component.desc"
          :class="[
            'px-3 py-1.5 rounded-full text-xs transition-all duration-200',
            selectedComponents.includes(component.id)
              ? 'bg-blue-600 text-white border border-blue-400'
              : 'bg-slate-800 text-slate-300 border border-slate-600 hover:bg-slate-700'
          ]"
        >
          {{ component.name }}
        </button>
        <div v-if="currentComponents.length === 0" class="text-xs text-slate-500">
          当前底座暂无推荐组件
        </div>
      </div>
    </div>

    <div v-if="selectedComponentDefs.length > 0" class="mb-3 space-y-2">
      <div class="text-xs text-slate-400">组件参数预览 (JSON 示例)</div>
      <div
        v-for="component in selectedComponentDefs"
        :key="component.id"
        class="rounded-lg border border-slate-700 bg-slate-900/70 overflow-hidden"
      >
        <div class="px-3 py-2 text-xs font-semibold text-blue-300 border-b border-slate-700">
          {{ component.id }}
        </div>
        <pre class="px-3 py-2 text-[11px] text-slate-300 overflow-x-auto">{{ prettyJson(componentParamExamples[component.id] || { enabled: true }) }}</pre>
      </div>
    </div>

    <div class="space-y-2">
      <label class="block text-xs text-slate-400">生成描述（可选）</label>
      <textarea
        v-model="workshopPrompt"
        rows="3"
        placeholder="例如：生成一个追击玩家的守卫，具备巡逻与视野检测能力。"
        class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
      />
      <button
        @click="generateEntity"
        :disabled="isLoading"
        class="w-full py-2 bg-cyan-700 hover:bg-cyan-600 disabled:bg-slate-700 rounded-lg text-sm text-white font-medium transition-colors duration-200"
      >
        {{ currentSelectedSprite ? '一键视觉化组装' : '一键生成实体' }}
      </button>
    </div>
  </div>
</template>
