#!/usr/bin/env python
"""测试 AI 生成叙事结构功能

测试三个核心功能：
1. AI 生成幕标题和描述
2. AI 判断幕是否完成
3. 自动创建下一幕/卷/部
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from application.services.story_structure_ai_service import StoryStructureAIService
from infrastructure.persistence.database.story_node_repository import StoryNodeRepository
from infrastructure.ai.providers.anthropic_provider import AnthropicProvider
from infrastructure.ai.config.settings import Settings
from application.paths import DATA_DIR


async def test_ai_structure():
    """测试 AI 叙事结构生成"""

    # 初始化服务
    db_path = str(DATA_DIR / "aitext.db")
    repository = StoryNodeRepository(db_path)

    # 获取 LLM 服务
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        print("❌ 未找到 ANTHROPIC_API_KEY，将使用降级模式")
        llm_service = None
    else:
        settings = Settings(
            api_key=api_key.strip(),
            base_url=os.getenv("ANTHROPIC_BASE_URL")
        )
        llm_service = AnthropicProvider(settings)
        print("✅ LLM 服务已初始化")

    ai_service = StoryStructureAIService(repository, llm_service)

    # 测试小说 ID
    test_novel_id = "test-ai-structure"

    print("\n" + "="*60)
    print("测试 1: AI 生成第一幕标题和描述")
    print("="*60)

    # 清理旧数据
    tree = repository.get_tree(test_novel_id)
    for node in tree.nodes:
        repository.delete(node.id)
    print(f"✅ 已清理旧数据")

    # 初始化第一幕
    result = await ai_service.initialize_first_act(test_novel_id)
    print(f"\n结果: {result}")

    if result["success"]:
        print(f"✅ 第一幕已创建")
        print(f"   标题: {result['act_title']}")

        # 获取完整节点信息
        act_node = repository.get_by_id(result['act_id'])
        print(f"   描述: {act_node.description}")
        print(f"   ID: {act_node.id}")
    else:
        print(f"❌ 创建失败: {result['message']}")
        return

    print("\n" + "="*60)
    print("测试 2: AI 判断幕是否完成")
    print("="*60)

    # 模拟完成 5 章
    print("\n模拟场景: 已完成 5 章")
    result = await ai_service.check_act_completion(test_novel_id, 5)
    print(f"结果: {result}")
    print(f"   幕是否完成: {result['act_completed']}")
    print(f"   是否需要创建下一幕: {result['should_create_next']}")
    print(f"   当前幕章节数: {result['chapters_in_act']}")

    # 模拟完成 10 章
    print("\n模拟场景: 已完成 10 章")
    result = await ai_service.check_act_completion(test_novel_id, 10)
    print(f"结果: {result}")
    print(f"   幕是否完成: {result['act_completed']}")
    print(f"   是否需要创建下一幕: {result['should_create_next']}")

    if result['should_create_next']:
        print("\n" + "="*60)
        print("测试 3: 自动创建下一幕")
        print("="*60)

        current_act_id = result['current_act_id']
        next_result = await ai_service.create_next_act(test_novel_id, current_act_id)
        print(f"\n结果: {next_result}")

        if next_result["success"]:
            print(f"✅ 第 {next_result['act_number']} 幕已创建")
            print(f"   标题: {next_result['act_title']}")

            # 获取完整节点信息
            act_node = repository.get_by_id(next_result['act_id'])
            print(f"   描述: {act_node.description}")
            print(f"   ID: {act_node.id}")
        else:
            print(f"❌ 创建失败: {next_result['message']}")

    print("\n" + "="*60)
    print("测试完成！查看完整结构树")
    print("="*60)

    tree = repository.get_tree(test_novel_id)
    print(f"\n小说 {test_novel_id} 的结构:")
    for node in tree.nodes:
        indent = "  " * (node.level - 3)  # act 是 level 3
        print(f"{indent}{node.icon} {node.display_name}")
        print(f"{indent}   描述: {node.description}")


if __name__ == "__main__":
    asyncio.run(test_ai_structure())
