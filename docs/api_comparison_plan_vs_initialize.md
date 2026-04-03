# API 对比：初始规划 vs 继续规划

## 概述

系统中有两个容易混淆的"规划"接口，它们的功能和使用场景完全不同。

---

## 1. POST /novels/{id}/structure/plan - 结构规划（幕结构）

**文件位置：** `interfaces/api/v1/story_structure.py`

**底层实现：** `StoryStructureAIService.initialize_first_act()`

### 功能
- **创建叙事结构的第一幕**（Act）
- 只在小说创建后**首次调用一次**
- 生成幕的标题和描述（使用 AI）
- 不创建章节，只创建结构框架

### 前置条件
- ✅ 小说已创建
- ✅ Bible（世界观设定）已生成
- ✅ Bible 中有文风设定
- ❌ 不能已有幕结构（会检查并拒绝重复创建）

### 返回结果
```json
{
  "success": true,
  "message": "第一幕已创建",
  "nodes_created": 1,
  "act_id": "act-novel-123-1",
  "act_title": "序章：命运的开端"
}
```

### 后续流程
创建第一幕后，系统会在写作过程中**自动判断**何时结束当前幕并创建下一幕：
1. 每次章节生成完成后调用 `check_act_completion()`
2. AI 判断当前幕是否应该结束
3. 如果应该结束，自动调用 `create_next_act()` 创建下一幕

### 使用场景
```
用户创建小说 "修仙传"
  ↓
生成 Bible（世界观、人物、文风）
  ↓
用户确认 Bible
  ↓
【调用此接口】POST /structure/plan
  ↓
创建第一幕："序章：踏入仙途"
  ↓
用户开始写第 1 章、第 2 章...
  ↓
写到第 5 章时，AI 判断第一幕应该结束
  ↓
自动创建第二幕："成长：试炼之路"
```

---

## 2. POST /novels/{id}/plan - 章节大纲规划

**文件位置：** `interfaces/api/v1/generation.py`

**底层实现：** `AutoNovelGenerationWorkflow.suggest_outline()`

### 功能
- **为前 5 章生成详细大纲**
- 创建章节实体（Chapter）
- 为每章生成具体的情节大纲（使用 AI）
- 可以多次调用（支持 mode=revise 重新规划）

### 前置条件
- ✅ 小说已创建
- ✅ Bible 已生成（用于生成大纲时参考）
- ⚠️ 不强制要求幕结构存在

### 请求参数
```json
{
  "mode": "initial",  // initial=首次规划, revise=重新规划
  "dry_run": false    // true=预演模式，不调用 LLM
}
```

### 返回结果
```json
{
  "success": true,
  "message": "成功生成 5 章大纲",
  "bible_updated": false,
  "outline_updated": true,
  "chapters_planned": 5
}
```

### 生成的内容
为每章创建：
- 章节实体（Chapter）
- 章节编号和标题
- 详细大纲（情节梗概）

示例：
```
第 1 章：初入仙门
大纲：主角林风在山村遇到仙人，通过测试展现出惊人的灵根资质，
被带入青云宗。初次见到修仙世界的壮丽景象，内心震撼...

第 2 章：新人试炼
大纲：林风参加新弟子试炼，遇到傲慢的世家子弟挑衅。
在试炼中展现出过人的悟性，引起长老注意...
```

### 使用场景
```
用户创建小说 "修仙传"
  ↓
生成 Bible
  ↓
【调用此接口】POST /plan (mode=initial)
  ↓
生成前 5 章的详细大纲
  ↓
用户查看大纲，觉得第 3 章不满意
  ↓
【再次调用】POST /plan (mode=revise)
  ↓
重新生成大纲
  ↓
用户开始生成章节内容
```

---

## 3. 两者的关系

### 层级关系
```
小说（Novel）
  └─ 幕结构（Act）          ← structure/plan 创建
       ├─ 第一幕
       │   ├─ 第 1 章       ← /plan 创建章节和大纲
       │   ├─ 第 2 章
       │   └─ 第 3 章
       ├─ 第二幕
       │   ├─ 第 4 章
       │   └─ 第 5 章
       └─ 第三幕
           └─ ...
```

### 调用顺序
```
推荐流程：
1. POST /novels              创建小说
2. POST /bible/generate      生成世界观
3. POST /structure/plan      创建第一幕（结构框架）
4. POST /plan                生成前 5 章大纲（详细内容）
5. POST /generate-chapter    开始生成章节

也可以跳过步骤 3：
1. POST /novels
2. POST /bible/generate
3. POST /plan                直接生成章节大纲
4. POST /generate-chapter    开始生成章节
（此时没有幕结构，但不影响写作）
```

### 是否必需？

| 接口 | 是否必需 | 说明 |
|------|---------|------|
| `POST /structure/plan` | ❌ 可选 | 幕结构是高级功能，用于管理长篇小说的叙事节奏。短篇或不需要结构管理的可以跳过 |
| `POST /plan` | ⚠️ 推荐 | 不是必需的，可以直接生成章节。但有大纲可以让生成更连贯 |

---

## 4. 实际使用建议

### 场景 1：完整流程（推荐）
适合长篇小说，需要精细的结构管理：

```typescript
// 1. 创建小说
const novel = await novelApi.createNovel({...})

// 2. 生成 Bible
await bibleApi.generateBible(novel.id)
await pollBibleStatus(novel.id)

// 3. 创建幕结构
await structureApi.planStructure(novel.id)

// 4. 生成章节大纲
await workflowApi.aiPlan(novel.id, { mode: 'initial' })

// 5. 开始写作
await workflowApi.generateChapter(novel.id, 1)
```

### 场景 2：快速开始（简化）
适合短篇或快速原型：

```typescript
// 1. 创建小说
const novel = await novelApi.createNovel({...})

// 2. 生成 Bible
await bibleApi.generateBible(novel.id)

// 3. 生成章节大纲（跳过幕结构）
await workflowApi.aiPlan(novel.id, { mode: 'initial' })

// 4. 开始写作
await workflowApi.generateChapter(novel.id, 1)
```

### 场景 3：极简流程
适合实验性写作：

```typescript
// 1. 创建小说
const novel = await novelApi.createNovel({...})

// 2. 直接生成章节（跳过 Bible 和大纲）
await workflowApi.generateChapter(novel.id, 1)
```

---

## 5. 前端集成建议

### 更新 frontend_integration_plan.md

之前的文档中把 `POST /structure/plan` 列为高优先级，但实际上：

**优先级调整：**

1. **P0 - 必须实现**
   - `POST /plan` - 章节大纲规划
   - 这是核心功能，直接影响写作质量

2. **P1 - 推荐实现**
   - `POST /structure/plan` - 幕结构规划
   - 这是高级功能，用于长篇小说的结构管理

3. **P2 - 可选实现**
   - 一致性检查、故事线管理等

### 前端 UI 建议

**Home.vue - 创建小说流程**

```vue
<n-steps :current="currentStep">
  <n-step title="创建小说" />
  <n-step title="生成世界观" />
  <n-step title="规划大纲" />  <!-- 这里是 POST /plan -->
  <n-step title="开始写作" />
</n-steps>

<!-- 第 3 步：规划大纲 -->
<div v-if="currentStep === 2">
  <n-space vertical>
    <n-alert type="info">
      AI 将为您生成前 5 章的详细大纲，您可以随时修改
    </n-alert>

    <n-button
      type="primary"
      @click="handlePlanOutline"
      :loading="planning"
    >
      生成章节大纲
    </n-button>

    <!-- 可选：高级选项 -->
    <n-collapse>
      <n-collapse-item title="高级选项">
        <n-checkbox v-model:checked="createActStructure">
          同时创建幕结构（适合长篇小说）
        </n-checkbox>
      </n-collapse-item>
    </n-collapse>
  </n-space>
</div>
```

**Workbench.vue - 工作台操作**

```vue
<!-- 顶部操作栏 -->
<n-space>
  <!-- 章节大纲管理 -->
  <n-button @click="showOutlinePanel = true">
    <template #icon><n-icon><IconOutline /></n-icon></template>
    章节大纲
  </n-button>

  <!-- 幕结构管理（可选） -->
  <n-button
    v-if="hasActStructure"
    @click="showStructurePanel = true"
  >
    <template #icon><n-icon><IconStructure /></n-icon></template>
    幕结构
  </n-button>
</n-space>
```

---

## 6. 总结

| 对比项 | POST /structure/plan | POST /plan |
|--------|---------------------|-----------|
| **功能** | 创建幕结构（框架） | 生成章节大纲（内容） |
| **调用时机** | 创建小说后首次调用 | 可多次调用 |
| **生成内容** | 第一幕的标题和描述 | 前 5 章的详细大纲 |
| **是否必需** | ❌ 可选（高级功能） | ⚠️ 推荐（提升质量） |
| **使用场景** | 长篇小说结构管理 | 所有小说的大纲规划 |
| **前端优先级** | P1（推荐） | P0（必须） |

**关键区别：**
- `structure/plan` 是**结构层**的规划（幕、卷、部）
- `/plan` 是**内容层**的规划（章节大纲）

两者可以独立使用，也可以配合使用。对于大多数用户，**只需要 `/plan` 就够了**。
