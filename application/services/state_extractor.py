import json
import logging
from domain.ai.services.llm_service import LLMService, GenerationConfig
from domain.ai.value_objects.prompt import Prompt
from domain.novel.value_objects.chapter_state import ChapterState

logger = logging.getLogger(__name__)

_EMPTY_STATE = {
    "new_characters": [],
    "character_actions": [],
    "relationship_changes": [],
    "foreshadowing_planted": [],
    "foreshadowing_resolved": [],
    "events": []
}


class StateExtractor:
    """状态提取应用服务

    使用 LLM 从章节内容中提取结构化信息
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def extract_chapter_state(self, content: str) -> ChapterState:
        """从章节内容中提取状态

        Args:
            content: 章节内容

        Returns:
            提取的章节状态
        """
        logger.info(f"StateExtractor.extract_chapter_state: content_length={len(content)}")

        # 构建提取提示词
        system_prompt, user_prompt = self._build_extraction_prompt(content)
        prompt = Prompt(system=system_prompt, user=user_prompt)

        # 配置 LLM
        config = GenerationConfig(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            temperature=0.3
        )

        # 调用 LLM 生成
        result = await self.llm_service.generate(prompt=prompt, config=config)
        raw_response = result.content
        logger.debug(f"StateExtractor LLM raw response (first 500 chars): {raw_response[:500]}")

        # 解析 JSON 结果（处理 markdown 代码块）
        data = self._parse_json_response(raw_response)

        chapter_state = ChapterState(
            new_characters=data.get("new_characters", []),
            character_actions=data.get("character_actions", []),
            relationship_changes=data.get("relationship_changes", []),
            foreshadowing_planted=data.get("foreshadowing_planted", []),
            foreshadowing_resolved=data.get("foreshadowing_resolved", []),
            events=data.get("events", [])
        )
        logger.info(
            f"StateExtractor result: "
            f"new_characters={len(chapter_state.new_characters)}, "
            f"character_actions={len(chapter_state.character_actions)}, "
            f"relationship_changes={len(chapter_state.relationship_changes)}, "
            f"foreshadowing_planted={len(chapter_state.foreshadowing_planted)}, "
            f"foreshadowing_resolved={len(chapter_state.foreshadowing_resolved)}, "
            f"events={len(chapter_state.events)}"
        )
        return chapter_state

    def _parse_json_response(self, raw: str) -> dict:
        """解析 LLM 返回的 JSON，处理 markdown 代码块包装"""
        content = raw.strip()

        # 移除 markdown 代码块标记
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()

        # 尝试找到第一个 { 和最后一个 }
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end + 1]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"StateExtractor failed to parse JSON: {e}. Raw (first 300): {raw[:300]}")
            return dict(_EMPTY_STATE)

    def _build_extraction_prompt(self, content: str) -> tuple[str, str]:
        """构建提取提示词

        Args:
            content: 章节内容

        Returns:
            (system_prompt, user_prompt) 元组
        """
        system_prompt = """你是一个专业的小说内容分析助手。你的任务是从章节内容中提取结构化信息。

请提取以下信息并以 JSON 格式返回：
1. new_characters: 新出现的角色列表，每个角色包含 name（名字）、description（描述）、first_appearance（首次出现章节号）
2. character_actions: 角色行为列表，每个行为包含 character_id（角色ID）、action（行为描述）、chapter（章节号）
3. relationship_changes: 关系变化列表，每个变化包含 char1（角色1 ID）、char2（角色2 ID）、old_type（旧关系类型）、new_type（新关系类型）、chapter（章节号）
4. foreshadowing_planted: 埋下的伏笔列表，每个伏笔包含 description（描述）、chapter（章节号）
5. foreshadowing_resolved: 解决的伏笔列表，每个解决包含 foreshadowing_id（伏笔ID）、chapter（章节号）
6. events: 事件列表，每个事件包含 type（类型）、description（描述）、involved_characters（涉及的角色ID列表）、chapter（章节号）

返回格式：
{
  "new_characters": [...],
  "character_actions": [...],
  "relationship_changes": [...],
  "foreshadowing_planted": [...],
  "foreshadowing_resolved": [...],
  "events": [...]
}

只返回 JSON，不要包含其他文本。"""

        user_prompt = f"""请从以下章节内容中提取结构化信息：

{content}"""

        return system_prompt, user_prompt
