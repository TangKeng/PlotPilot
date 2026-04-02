# Superpowers 集成计划 V3

## 当前状态分析

### 已完成的工作
- ✅ StateExtractor 和 StateUpdater 已集成到 AutoNovelGenerationWorkflow
- ✅ 依赖注入配置已完成
- ✅ 代码可以正常运行，章节生成成功

### 发现的问题
1. **StateUpdater 未真正工作**
   - Bible 文件修改时间未更新（停留在 2026-04-02 21:47:14）
   - 生成第 3 章后，Bible 数据没有变化
   - 可能原因：
     - StateExtractor 提取的数据为空
     - StateUpdater 的更新逻辑有问题
     - 异常被捕获但未记录

2. **缺少日志系统**
   - 无法查看 StateExtractor 和 StateUpdater 的执行情况
   - 无法确认是否有异常发生

3. **Knowledge 数据缺失**
   - test-quality-1 没有 Knowledge 文件
   - 没有 AutoKnowledgeGenerator 服务

4. **ConsistencyChecker 使用空数据**
   - 创建临时空对象而非加载真实数据

## 修复计划

### Phase 1: 调试 StateExtractor 和 StateUpdater（优先级：最高）

#### 1.1 添加详细日志
- [ ] 在 StateExtractor.extract_chapter_state 中添加日志
  - 记录输入的章节内容长度
  - 记录 LLM 返回的原始响应
  - 记录解析后的 ChapterState 内容

- [ ] 在 StateUpdater.update_from_chapter 中添加日志
  - 记录接收到的 ChapterState
  - 记录每个更新操作（新角色、关系变化、伏笔等）
  - 记录 Bible 保存操作

- [ ] 在 AutoNovelGenerationWorkflow 中添加日志
  - 记录 StateExtractor 调用前后
  - 记录 StateUpdater 调用前后
  - 记录所有异常详情

#### 1.2 验证 StateExtractor 提取逻辑
- [ ] 检查 LLM prompt 是否正确
- [ ] 检查返回数据的解析逻辑
- [ ] 添加单元测试验证提取功能

#### 1.3 验证 StateUpdater 更新逻辑
- [ ] 检查 Bible 仓储的保存方法
- [ ] 确认文件写入权限
- [ ] 添加单元测试验证更新功能

#### 1.4 修复方法名不一致问题
- [ ] 确认 StateUpdater 的方法名
  - 当前：`update_from_chapter`
  - Workflow 调用：`update_from_chapter`（已对齐）

### Phase 2: 实现 Knowledge 自动生成（优先级：高）

#### 2.1 创建 AutoKnowledgeGenerator
- [ ] 实现 KnowledgeGenerator 服务
  - 生成初始梗概（premise_lock）
  - 生成章节摘要（chapters）
  - 提取知识三元组（facts）

#### 2.2 集成到创建小说流程
- [ ] 修改 novels.py 的 create_novel 端点
  - 在生成 Bible 后生成 Knowledge
  - 或提供异步生成选项

#### 2.3 集成到章节生成流程
- [ ] 在 StateUpdater 中添加 Knowledge 更新逻辑
  - 更新章节摘要
  - 添加新的知识三元组

### Phase 3: 修复 ConsistencyChecker（优先级：中）

#### 3.1 修改 _check_consistency 方法
- [ ] 从 BibleRepository 加载真实 Bible 数据
- [ ] 从 CharacterRegistry 加载真实角色数据
- [ ] 从 KnowledgeService 加载 Knowledge 数据

#### 3.2 增强一致性检查
- [ ] 检查角色行为是否符合设定
- [ ] 检查地点描述是否一致
- [ ] 检查时间线是否合理
- [ ] 检查伏笔是否得到解决

### Phase 4: 集成向量检索（优先级：中）

#### 4.1 配置 VectorStore
- [ ] 配置 Qdrant 连接
- [ ] 或使用内存向量存储（开发环境）

#### 4.2 集成 IndexingService
- [ ] 在章节生成后自动索引
- [ ] 索引章节内容、角色、地点

#### 4.3 增强 ContextBuilder
- [ ] 使用向量检索查找相关历史章节
- [ ] 使用语义搜索查找相关角色

### Phase 5: 集成智能人物管理（优先级：低）

#### 5.1 CharacterRegistry 真实化
- [ ] 从 Bible 加载角色到 CharacterRegistry
- [ ] 实现角色重要性分层
- [ ] 实现活跃度追踪

#### 5.2 集成 AppearanceScheduler
- [ ] 在生成章节前调度角色出场
- [ ] 根据故事线安排角色

#### 5.3 集成 CharacterIndexer
- [ ] 索引角色信息到向量数据库
- [ ] 支持语义搜索角色

### Phase 6: 前端集成（优先级：低）

#### 6.1 优化 BiblePanel
- [ ] 显示自动提取的新角色
- [ ] 显示角色关系图
- [ ] 支持手动编辑和确认

#### 6.2 优化 KnowledgePanel
- [ ] 显示自动生成的梗概
- [ ] 显示章节摘要
- [ ] 显示知识三元组图谱
- [ ] 支持向量检索

#### 6.3 优化 ConsistencyReportPanel
- [ ] 显示详细的一致性问题
- [ ] 提供修复建议
- [ ] 支持一键修复

## 时间估算

- Phase 1: 1-2 天（调试和修复）
- Phase 2: 2-3 天（实现 Knowledge 生成）
- Phase 3: 1 天（修复 ConsistencyChecker）
- Phase 4: 2-3 天（集成向量检索）
- Phase 5: 2-3 天（智能人物管理）
- Phase 6: 3-4 天（前端集成）

**总计：11-16 天**

## 立即行动项

1. **添加日志系统**（30 分钟）
   - 在关键位置添加 logger.info/debug
   - 确保可以看到执行流程

2. **重新生成章节并查看日志**（10 分钟）
   - 确认 StateExtractor 是否被调用
   - 确认提取了什么数据
   - 确认 StateUpdater 是否执行

3. **修复发现的问题**（1-2 小时）
   - 根据日志定位问题
   - 修复代码
   - 验证修复效果

4. **提交代码**（5 分钟）
   - Git commit
   - 更新文档

## 成功标准

### Phase 1 成功标准
- ✅ 生成章节后 Bible 文件被更新
- ✅ 新角色被自动添加到 Bible
- ✅ 角色关系被自动更新
- ✅ 伏笔被正确记录

### Phase 2 成功标准
- ✅ 创建小说时自动生成 Knowledge
- ✅ 生成章节后自动更新章节摘要
- ✅ 知识三元组被正确提取

### Phase 3 成功标准
- ✅ ConsistencyChecker 使用真实数据
- ✅ 能够检测出真实的一致性问题
- ✅ 提供有价值的修复建议

### Phase 4 成功标准
- ✅ 章节内容被索引到向量数据库
- ✅ ContextBuilder 可以使用语义检索
- ✅ 生成质量提升

### Phase 5 成功标准
- ✅ CharacterRegistry 包含真实角色数据
- ✅ AppearanceScheduler 智能安排出场
- ✅ 角色出场更加合理

### Phase 6 成功标准
- ✅ 前端可以显示自动提取的数据
- ✅ 用户可以编辑和确认
- ✅ UI 流畅易用

## 风险和依赖

### 风险
1. **LLM 提取不准确**
   - 缓解：优化 prompt，添加示例
   - 缓解：添加人工审核机制

2. **向量数据库配置复杂**
   - 缓解：先使用内存存储
   - 缓解：提供详细配置文档

3. **性能问题**
   - 缓解：异步处理
   - 缓解：添加缓存

### 依赖
1. **Anthropic API**
   - 需要有效的 API key
   - 需要足够的配额

2. **Qdrant（可选）**
   - 可以使用内存存储替代

3. **OpenAI Embedding（可选）**
   - 可以使用其他 embedding 服务

## 下一步

**立即开始 Phase 1.1：添加详细日志**
