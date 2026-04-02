"""自动 Knowledge 生成器 - 从小说 Bible 生成初始知识图谱"""
import logging
import json
from typing import Dict, Any
from domain.ai.services.llm_service import LLMService, GenerationConfig
from domain.ai.value_objects.prompt import Prompt
from application.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


class AutoKnowledgeGenerator:
    """自动 Knowledge 生成器

    根据小说标题和 Bible 内容，使用 LLM 生成：
    - premise_lock（核心梗概）
    - 初始知识三元组（facts）
    """

    def __init__(self, llm_service: LLMService, knowledge_service: KnowledgeService):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service

    async def generate_and_save(
        self,
        novel_id: str,
        title: str,
        bible_summary: str = ""
    ) -> Dict[str, Any]:
        """生成并保存初始 Knowledge

        Args:
            novel_id: 小说 ID
            title: 小说标题
            bible_summary: Bible 摘要（可选，提升生成质量）

        Returns:
            生成的 Knowledge 数据
        """
        logger.info(f"AutoKnowledgeGenerator: generating knowledge for novel '{title}' ({novel_id})")

        knowledge_data = await self._generate_knowledge_data(title, bible_summary)

        self._save_to_knowledge(novel_id, knowledge_data)

        logger.info(
            f"Knowledge generated for {novel_id}: "
            f"facts={len(knowledge_data.get('facts', []))}"
        )
        return knowledge_data

    async def _generate_knowledge_data(self, title: str, bible_summary: str) -> Dict[str, Any]:
        """使用 LLM 生成 Knowledge 数据"""

        context_section = f"\n\n**小说设定摘要：**\n{bible_summary}" if bible_summary.strip() else ""

        system_prompt = """你是专业的小说知识图谱构建助手。根据小说标题和设定，生成核心知识。

**重要：只输出 JSON，不要有任何其他文字。**

JSON 格式：
{
  "premise_lock": "一句话核心梗概（50-100字，概括故事主线、主角目标、核心冲突）",
  "facts": [
    {
      "id": "fact-001",
      "subject": "主语（角色名/地点名/概念）",
      "predicate": "关系谓词（如：是、属于、位于、能力是、目标是）",
      "object": "宾语",
      "note": "说明（可空）"
    }
  ]
}

facts 要求：
- 提取 5-10 条核心世界观设定知识三元组
- 覆盖主要角色身份、核心地点、关键规则/能力设定
- 只写确定的设定，不要推测"""

        user_prompt = f"小说标题：《{title}》{context_section}\n\n请生成初始知识图谱。只输出 JSON。"

        prompt = Prompt(system=system_prompt, user=user_prompt)
        config = GenerationConfig(max_tokens=2048, temperature=0.4)

        result = await self.llm_service.generate(prompt, config)

        return self._parse_json_response(result.content)

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON，处理 markdown 代码块包装"""
        content = raw.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()

        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end + 1]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"AutoKnowledgeGenerator failed to parse JSON: {e}")
            return {"premise_lock": "", "facts": []}

    def _save_to_knowledge(self, novel_id: str, knowledge_data: Dict[str, Any]) -> None:
        """保存到 Knowledge"""
        premise_lock = knowledge_data.get("premise_lock", "")
        facts_data = knowledge_data.get("facts", [])

        # 构建完整的 knowledge 数据结构
        data = {
            "version": 1,
            "premise_lock": premise_lock,
            "chapters": [],
            "facts": [
                {
                    "id": f.get("id", f"fact-{i+1:03d}"),
                    "subject": f.get("subject", ""),
                    "predicate": f.get("predicate", ""),
                    "object": f.get("object", ""),
                    "chapter_id": None,
                    "note": f.get("note", "")
                }
                for i, f in enumerate(facts_data)
            ]
        }

        self.knowledge_service.update_knowledge(novel_id, data)
        logger.debug(f"Saved knowledge for {novel_id}: premise_lock={bool(premise_lock)}, facts={len(facts_data)}")
