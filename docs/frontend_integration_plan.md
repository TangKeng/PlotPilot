# 未使用 API 的前端集成方案

本文档提供 6 个已实现但未使用的后端 API 的前端集成建议。

## 📋 API 集成优先级

### 🔴 高优先级 (P0)

#### 1. POST /novels/{id}/structure/plan - 手动触发结构规划

**现状：**
- 后端已实现，用于替代自动生成流程
- 前端尚未集成，创建小说后无法手动触发规划

**业务价值：**
- 完成新的小说创建流程：创建 → 生成 Bible → 确认 → 手动规划
- 让用户掌控规划时机，避免自动生成不符合预期

**集成方案：**

##### 1.1 后端接口
```typescript
// web-app/src/api/structure.ts
export const structureApi = {
  /**
   * POST /api/v1/novels/{novel_id}/structure/plan
   * 手动触发结构规划（生成章节大纲和幕结构）
   */
  planStructure: (novelId: string) =>
    apiClient.post<{
      message: string
      acts_created: number
      chapters_planned: number
    }>(`/novels/${novelId}/structure/plan`),
}
```

##### 1.2 前端 UI 集成位置

**位置 1：Home.vue - 创建小说后的引导流程**

```typescript
// web-app/src/views/Home.vue
const handleCreate = async () => {
  creating.value = true
  try {
    // 1. 创建小说
    const result = await novelApi.createNovel(payload)
    message.success('小说创建成功')

    // 2. 触发 Bible 生成
    await bibleApi.generateBible(result.id)
    message.info('正在生成世界观设定...')

    // 3. 轮询 Bible 状态
    const bibleReady = await pollBibleStatus(result.id)

    if (bibleReady) {
      // 4. 弹窗确认是否开始规划
      dialog.create({
        title: '世界观设定已生成',
        content: '是否立即开始规划章节结构？',
        positiveText: '开始规划',
        negativeText: '稍后手动规划',
        onPositiveClick: async () => {
          await structureApi.planStructure(result.id)
          message.success('结构规划完成')
          router.push(`/book/${result.id}/workbench`)
        },
        onNegativeClick: () => {
          router.push(`/book/${result.id}/workbench`)
        }
      })
    }
  } catch (error) {
    message.error('创建失败')
  } finally {
    creating.value = false
  }
}

// 轮询 Bible 状态
const pollBibleStatus = async (novelId: string, maxAttempts = 30) => {
  for (let i = 0; i < maxAttempts; i++) {
    const status = await bibleApi.getBibleStatus(novelId)
    if (status.ready) return true
    await new Promise(resolve => setTimeout(resolve, 2000))
  }
  return false
}
```

**位置 2：Workbench.vue - 工作台顶部操作栏**

在 `StatsTopBar.vue` 组件中添加"规划结构"按钮：

```vue
<!-- web-app/src/components/stats/StatsTopBar.vue -->
<template>
  <div class="stats-top-bar">
    <!-- 现有内容 -->

    <!-- 新增：结构规划按钮 -->
    <n-button
      v-if="!hasStructure"
      type="primary"
      @click="handlePlanStructure"
      :loading="planning"
    >
      <template #icon>
        <n-icon><IconPlan /></n-icon>
      </template>
      规划章节结构
    </n-button>
  </div>
</template>

<script setup lang="ts">
const planning = ref(false)
const hasStructure = ref(false)

const checkStructure = async () => {
  const structure = await structureApi.getStructure(props.slug)
  hasStructure.value = structure.children.length > 0
}

const handlePlanStructure = async () => {
  planning.value = true
  try {
    await structureApi.planStructure(props.slug)
    message.success('结构规划完成')
    hasStructure.value = true
    emit('refresh')
  } catch (error) {
    message.error('规划失败')
  } finally {
    planning.value = false
  }
}

onMounted(() => {
  checkStructure()
})
</script>
```

---

### 🟡 中优先级 (P1)

#### 2. GET /novels/{id}/consistency-report - 一致性分析报告

**现状：**
- 后端已实现（目前返回空报告）
- 前端已定义接口但未调用

**业务价值：**
- 检测章节间的矛盾（人物设定、时间线、地点描述等）
- 提升小说质量，减少逻辑错误

**集成方案：**

##### 2.1 后端增强
```python
# interfaces/api/v1/generation.py
@router.get("/{novel_id}/consistency-report")
async def get_consistency_report(
    novel_id: str,
    chapter: Optional[int] = None,  # 可选：检查特定章节
    workflow: AutoNovelGenerationWorkflow = Depends(get_auto_workflow)
):
    """获取一致性分析报告

    检查内容：
    - 人物设定前后矛盾
    - 时间线错误
    - 地点描述不一致
    - 情节逻辑漏洞
    """
    # TODO: 实现真正的一致性检查逻辑
    # 1. 读取所有章节内容
    # 2. 提取关键信息（人物、地点、时间）
    # 3. 对比 Bible 设定
    # 4. 使用 LLM 分析矛盾

    return ConsistencyReportResponse(
        issues=[
            {
                "type": "character",
                "severity": "high",
                "chapter": 3,
                "description": "第3章中主角身高描述为180cm，与第1章的175cm矛盾"
            }
        ],
        warnings=[
            {
                "type": "timeline",
                "severity": "medium",
                "chapter": 5,
                "description": "第5章时间线可能存在跳跃"
            }
        ],
        suggestions=[
            "建议统一主角身高设定",
            "建议补充第4-5章之间的时间过渡"
        ]
    )
```

##### 2.2 前端 UI 集成

**位置：WorkArea.vue - 章节编辑器右上角**

```vue
<!-- web-app/src/components/workbench/WorkArea.vue -->
<template>
  <div class="work-area">
    <div class="toolbar">
      <!-- 现有按钮 -->

      <!-- 新增：一致性检查按钮 -->
      <n-button
        text
        @click="handleConsistencyCheck"
        :loading="checking"
      >
        <template #icon>
          <n-icon><IconCheck /></n-icon>
        </template>
        一致性检查
      </n-button>
    </div>

    <!-- 一致性报告抽屉 -->
    <n-drawer
      v-model:show="showReport"
      :width="400"
      placement="right"
    >
      <n-drawer-content title="一致性分析报告">
        <ConsistencyReport :report="report" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
const checking = ref(false)
const showReport = ref(false)
const report = ref(null)

const handleConsistencyCheck = async () => {
  checking.value = true
  try {
    report.value = await workflowApi.getConsistencyReport(
      props.slug,
      props.currentChapterId
    )
    showReport.value = true

    // 显示问题数量
    const issueCount = report.value.issues.length
    if (issueCount > 0) {
      message.warning(`发现 ${issueCount} 个一致性问题`)
    } else {
      message.success('未发现一致性问题')
    }
  } catch (error) {
    message.error('检查失败')
  } finally {
    checking.value = false
  }
}
</script>
```

**新增组件：ConsistencyReport.vue**

```vue
<!-- web-app/src/components/workbench/ConsistencyReport.vue -->
<template>
  <div class="consistency-report">
    <!-- 严重问题 -->
    <n-alert
      v-for="issue in report.issues"
      :key="issue.description"
      type="error"
      :title="`第 ${issue.chapter} 章 - ${getTypeLabel(issue.type)}`"
      style="margin-bottom: 12px"
    >
      {{ issue.description }}
    </n-alert>

    <!-- 警告 -->
    <n-alert
      v-for="warning in report.warnings"
      :key="warning.description"
      type="warning"
      :title="`第 ${warning.chapter} 章 - ${getTypeLabel(warning.type)}`"
      style="margin-bottom: 12px"
    >
      {{ warning.description }}
    </n-alert>

    <!-- 建议 -->
    <n-card v-if="report.suggestions.length > 0" title="改进建议">
      <ul>
        <li v-for="(suggestion, idx) in report.suggestions" :key="idx">
          {{ suggestion }}
        </li>
      </ul>
    </n-card>
  </div>
</template>

<script setup lang="ts">
const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    character: '人物设定',
    timeline: '时间线',
    location: '地点描述',
    plot: '情节逻辑',
  }
  return labels[type] || type
}
</script>
```

---

#### 3. GET/POST /novels/{id}/storylines - 故事线管理

**现状：**
- 后端已实现完整的 CRUD
- 前端完全未集成

**业务价值：**
- 管理多条故事线（主线、支线、暗线）
- 跟踪每条故事线的进度和状态
- 确保故事线在合适的章节展开和收尾

**集成方案：**

##### 3.1 前端接口定义

```typescript
// web-app/src/api/storyline.ts
export interface Storyline {
  id: string
  storyline_type: 'main' | 'sub' | 'hidden'
  status: 'planned' | 'active' | 'completed'
  estimated_chapter_start: number
  estimated_chapter_end: number
}

export const storylineApi = {
  /**
   * GET /api/v1/novels/{novel_id}/storylines
   */
  getStorylines: (novelId: string) =>
    apiClient.get<Storyline[]>(`/novels/${novelId}/storylines`),

  /**
   * POST /api/v1/novels/{novel_id}/storylines
   */
  createStoryline: (novelId: string, data: {
    storyline_type: string
    estimated_chapter_start: number
    estimated_chapter_end: number
  }) =>
    apiClient.post<Storyline>(`/novels/${novelId}/storylines`, data),
}
```

##### 3.2 前端 UI 集成

**位置：SettingsPanel.vue - 新增"故事线"标签页**

```vue
<!-- web-app/src/components/workbench/SettingsPanel.vue -->
<template>
  <n-tabs v-model:value="currentPanel" type="card">
    <n-tab-pane name="bible" tab="世界观">
      <BiblePanel />
    </n-tab-pane>

    <n-tab-pane name="knowledge" tab="知识库">
      <KnowledgePanel />
    </n-tab-pane>

    <!-- 新增：故事线标签页 -->
    <n-tab-pane name="storylines" tab="故事线">
      <StorylinePanel :slug="slug" />
    </n-tab-pane>
  </n-tabs>
</template>
```

**新增组件：StorylinePanel.vue**

```vue
<!-- web-app/src/components/workbench/StorylinePanel.vue -->
<template>
  <div class="storyline-panel">
    <div class="panel-header">
      <h3>故事线管理</h3>
      <n-button type="primary" @click="showCreateDialog = true">
        <template #icon>
          <n-icon><IconPlus /></n-icon>
        </template>
        添加故事线
      </n-button>
    </div>

    <n-spin :show="loading">
      <n-empty v-if="storylines.length === 0" description="暂无故事线" />

      <n-timeline v-else>
        <n-timeline-item
          v-for="storyline in storylines"
          :key="storyline.id"
          :type="getTimelineType(storyline.status)"
          :title="getTypeLabel(storyline.storyline_type)"
        >
          <template #icon>
            <n-icon :component="getIcon(storyline.storyline_type)" />
          </template>

          <div class="storyline-item">
            <n-tag :type="getStatusType(storyline.status)">
              {{ getStatusLabel(storyline.status) }}
            </n-tag>
            <p class="chapter-range">
              第 {{ storyline.estimated_chapter_start }} - {{ storyline.estimated_chapter_end }} 章
            </p>
          </div>
        </n-timeline-item>
      </n-timeline>
    </n-spin>

    <!-- 创建故事线对话框 -->
    <n-modal v-model:show="showCreateDialog" preset="dialog" title="添加故事线">
      <n-form ref="formRef" :model="formData">
        <n-form-item label="类型" path="storyline_type">
          <n-select
            v-model:value="formData.storyline_type"
            :options="typeOptions"
          />
        </n-form-item>

        <n-form-item label="起始章节" path="estimated_chapter_start">
          <n-input-number
            v-model:value="formData.estimated_chapter_start"
            :min="1"
          />
        </n-form-item>

        <n-form-item label="结束章节" path="estimated_chapter_end">
          <n-input-number
            v-model:value="formData.estimated_chapter_end"
            :min="formData.estimated_chapter_start"
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space>
          <n-button @click="showCreateDialog = false">取消</n-button>
          <n-button type="primary" @click="handleCreate">创建</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { storylineApi } from '@/api/storyline'

const props = defineProps<{ slug: string }>()
const message = useMessage()

const loading = ref(false)
const storylines = ref<Storyline[]>([])
const showCreateDialog = ref(false)
const formData = ref({
  storyline_type: 'main',
  estimated_chapter_start: 1,
  estimated_chapter_end: 10,
})

const typeOptions = [
  { label: '主线', value: 'main' },
  { label: '支线', value: 'sub' },
  { label: '暗线', value: 'hidden' },
]

const loadStorylines = async () => {
  loading.value = true
  try {
    storylines.value = await storylineApi.getStorylines(props.slug)
  } catch (error) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  try {
    await storylineApi.createStoryline(props.slug, formData.value)
    message.success('创建成功')
    showCreateDialog.value = false
    await loadStorylines()
  } catch (error) {
    message.error('创建失败')
  }
}

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    main: '主线',
    sub: '支线',
    hidden: '暗线',
  }
  return labels[type] || type
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    planned: '计划中',
    active: '进行中',
    completed: '已完成',
  }
  return labels[status] || status
}

onMounted(() => {
  loadStorylines()
})
</script>
```

---

### 🟢 低优先级 (P2)

#### 4. GET/POST /novels/{id}/plot-arc - 情节弧线管理

**现状：**
- 后端已实现
- 前端定义了接口但未调用

**业务价值：**
- 管理小说的情节发展曲线
- 确保节奏合理（起承转合）
- 可视化情节张力变化

**集成方案：**

类似故事线管理，但增加可视化图表：

```vue
<!-- web-app/src/components/workbench/PlotArcPanel.vue -->
<template>
  <div class="plot-arc-panel">
    <h3>情节弧线</h3>

    <!-- 使用 ECharts 或 Chart.js 绘制曲线图 -->
    <div ref="chartRef" class="plot-chart"></div>

    <!-- 关键节点列表 -->
    <n-list>
      <n-list-item v-for="point in keyPoints" :key="point.chapter">
        <template #prefix>
          <n-tag>第 {{ point.chapter }} 章</n-tag>
        </template>
        {{ point.description }}
      </n-list-item>
    </n-list>
  </div>
</template>
```

---

## 🎯 实施建议

### 第一阶段（本周）
1. ✅ 集成 `POST /structure/plan` - 完成新的小说创建流程
2. ✅ 在 Home.vue 添加 Bible 状态轮询和规划确认
3. ✅ 在 Workbench 添加"规划结构"按钮

### 第二阶段（下周）
4. 集成一致性检查功能
5. 增强后端一致性分析逻辑（使用 LLM）
6. 添加 ConsistencyReport 组件

### 第三阶段（未来）
7. 添加故事线管理功能
8. 添加情节弧线可视化
9. 评估是否需要这些高级功能

---

## 📝 技术要点

### 状态轮询最佳实践
```typescript
// 使用指数退避策略
const pollWithBackoff = async (
  checkFn: () => Promise<boolean>,
  maxAttempts = 30,
  initialDelay = 1000,
  maxDelay = 10000
) => {
  let delay = initialDelay

  for (let i = 0; i < maxAttempts; i++) {
    if (await checkFn()) return true

    await new Promise(resolve => setTimeout(resolve, delay))
    delay = Math.min(delay * 1.5, maxDelay)
  }

  return false
}
```

### 错误处理
```typescript
// 统一错误处理
const handleApiError = (error: any, defaultMessage: string) => {
  const detail = error?.response?.data?.detail
  message.error(detail || defaultMessage)
  console.error(error)
}
```

### 用户体验优化
- 使用 loading 状态避免重复点击
- 提供清晰的进度提示
- 失败时给出可操作的建议
- 支持取消长时间操作

---

## 🔗 相关文档

- [Backend API 实现状态分析](./backend_api_usage_analysis.md)
- [小说创建流程优化](../commits/e6ad109-aa3c4ad.md)
