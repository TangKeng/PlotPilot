<template>
  <n-modal
    v-model:show="visible"
    :mask-closable="false"
    :close-on-esc="false"
    preset="card"
    title="新书设置向导"
    style="width: 600px"
  >
    <n-steps :current="currentStep" :status="stepStatus">
      <n-step title="生成公约" description="AI 分析并生成世界观设定" />
      <n-step title="规划故事线" description="设计主线、支线和暗线" />
      <n-step title="设计情节弧" description="规划剧情张力曲线" />
      <n-step title="开始创作" description="进入工作台" />
    </n-steps>

    <div class="step-content">
      <!-- Step 1: Bible Generation -->
      <div v-if="currentStep === 1" class="step-panel">
        <n-alert v-if="bibleError" type="error" :title="bibleError" style="margin-bottom: 16px" />
        <n-spin :show="generatingBible">
          <div class="step-info">
            <n-icon size="48" color="#18a058">
              <IconBook />
            </n-icon>
            <h3>{{ bibleStatusText }}</h3>
            <p>AI 正在分析您的故事创意，生成角色、地点、时间线等设定...</p>
          </div>
        </n-spin>
      </div>

      <!-- Step 2: Storylines -->
      <div v-else-if="currentStep === 2" class="step-panel">
        <div class="step-info">
          <n-icon size="48" color="#2080f0">
            <IconTimeline />
          </n-icon>
          <h3>规划故事线</h3>
          <p>建议先设计故事的主线、支线和暗线，这将帮助 AI 更好地规划章节结构。</p>
          <n-space vertical size="small" style="margin-top: 16px; text-align: left">
            <div>• 主线：故事的核心发展脉络</div>
            <div>• 支线：丰富情节的次要线索</div>
            <div>• 暗线：隐藏的伏笔和线索</div>
          </n-space>
        </div>
      </div>

      <!-- Step 3: Plot Arc -->
      <div v-else-if="currentStep === 3" class="step-panel">
        <div class="step-info">
          <n-icon size="48" color="#f0a020">
            <IconChart />
          </n-icon>
          <h3>设计情节弧线</h3>
          <p>规划故事的起承转合，设置关键剧情点和张力变化。</p>
          <n-space vertical size="small" style="margin-top: 16px; text-align: left">
            <div>• 开端：故事的起点</div>
            <div>• 上升：矛盾逐渐激化</div>
            <div>• 转折：关键转折点</div>
            <div>• 高潮：矛盾最激烈时刻</div>
            <div>• 结局：故事的收尾</div>
          </n-space>
        </div>
      </div>

      <!-- Step 4: Complete -->
      <div v-else-if="currentStep === 4" class="step-panel">
        <div class="step-info">
          <n-icon size="48" color="#18a058">
            <IconCheck />
          </n-icon>
          <h3>准备就绪！</h3>
          <p>所有基础设置已完成，现在可以开始创作了。</p>
          <p style="margin-top: 12px; color: #666">您可以随时在工作台的"设置"面板中调整这些内容。</p>
        </div>
      </div>
    </div>

    <template #footer>
      <n-space justify="space-between">
        <n-button v-if="currentStep > 1 && currentStep < 4" @click="handleSkip">
          跳过向导
        </n-button>
        <div v-else></div>
        <n-space>
          <n-button v-if="currentStep === 2 || currentStep === 3" @click="handleNext">
            {{ currentStep === 3 ? '完成设置' : '下一步' }}
          </n-button>
          <n-button v-if="currentStep === 4" type="primary" @click="handleComplete">
            进入工作台
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { h, ref, watch, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { bibleApi } from '@/api/bible'

const IconBook = () =>
  h(
    'svg',
    { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'currentColor' },
    h('path', { d: 'M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z' })
  )

const IconTimeline = () =>
  h(
    'svg',
    { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'currentColor' },
    h('path', { d: 'M23 8c0 1.1-.9 2-2 2-.18 0-.35-.02-.51-.07l-3.56 3.55c.05.16.07.34.07.52 0 1.1-.9 2-2 2s-2-.9-2-2c0-.18.02-.36.07-.52l-2.55-2.55c-.16.05-.34.07-.52.07s-.36-.02-.52-.07l-4.55 4.56c.05.16.07.33.07.51 0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2c.18 0 .35.02.51.07l4.56-4.55C8.02 9.36 8 9.18 8 9c0-1.1.9-2 2-2s2 .9 2 2c0 .18-.02.36-.07.52l2.55 2.55c.16-.05.34-.07.52-.07s.36.02.52.07l3.55-3.56C19.02 8.35 19 8.18 19 8c0-1.1.9-2 2-2s2 .9 2 2z' })
  )

const IconChart = () =>
  h(
    'svg',
    { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'currentColor' },
    h('path', { d: 'M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z' })
  )

const IconCheck = () =>
  h(
    'svg',
    { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'currentColor' },
    h('path', { d: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z' })
  )

const props = defineProps<{
  novelId: string
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'complete'): void
  (e: 'skip'): void
}>()

const message = useMessage()

const visible = ref(props.show)
const currentStep = ref(1)
const stepStatus = ref<'process' | 'finish' | 'error' | 'wait'>('process')
const generatingBible = ref(false)
const bibleStatusText = ref('正在生成公约...')
const bibleError = ref('')

watch(() => props.show, (val) => {
  visible.value = val
  if (val) {
    currentStep.value = 1
    stepStatus.value = 'process'
    startBibleGeneration()
  }
})

// Initialize on mount if show is true
onMounted(() => {
  if (props.show) {
    startBibleGeneration()
  }
})

watch(visible, (val) => {
  emit('update:show', val)
})

const startBibleGeneration = async () => {
  generatingBible.value = true
  bibleError.value = ''

  try {
    // Trigger Bible generation
    await bibleApi.generateBible(props.novelId)
    bibleStatusText.value = '正在生成公约...'

    // Poll for completion
    const pollInterval = setInterval(async () => {
      try {
        const status = await bibleApi.getBibleStatus(props.novelId)

        if (status.ready) {
          clearInterval(pollInterval)
          generatingBible.value = false
          bibleStatusText.value = '公约生成完成！'

          // Auto advance after 1 second
          setTimeout(() => {
            currentStep.value = 2
          }, 1000)
        }
      } catch (error: any) {
        clearInterval(pollInterval)
        generatingBible.value = false
        bibleError.value = '检查状态失败，请刷新页面重试'
      }
    }, 2000)

    // Timeout after 2 minutes
    setTimeout(() => {
      clearInterval(pollInterval)
      if (generatingBible.value) {
        generatingBible.value = false
        bibleError.value = '生成超时，请稍后在工作台手动重试'
      }
    }, 120000)

  } catch (error: any) {
    generatingBible.value = false
    bibleError.value = error.response?.data?.detail || '生成失败，请重试'
  }
}

const handleNext = () => {
  if (currentStep.value < 4) {
    currentStep.value++
  }
}

const handleSkip = () => {
  emit('skip')
  visible.value = false
}

const handleComplete = () => {
  emit('complete')
  visible.value = false
}
</script>

<style scoped>
.step-content {
  margin: 32px 0;
  min-height: 280px;
}

.step-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.step-info {
  text-align: center;
  max-width: 480px;
}

.step-info h3 {
  margin: 16px 0 8px;
  font-size: 20px;
  font-weight: 600;
}

.step-info p {
  color: #666;
  line-height: 1.6;
  margin: 8px 0;
}
</style>
