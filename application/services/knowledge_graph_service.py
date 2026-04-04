"""
知识图谱自动推断服务
基于章节元素关联自动生成三元组
"""

import uuid
from typing import Dict, List, Tuple
from datetime import datetime

from domain.bible.triple import Triple, SourceType
from domain.structure.chapter_element import ChapterElement, ElementType, RelationType, Importance
from infrastructure.persistence.database.triple_repository import TripleRepository
from infrastructure.persistence.database.chapter_element_repository import ChapterElementRepository
from infrastructure.persistence.database.story_node_repository import StoryNodeRepository


class KnowledgeGraphService:
    """知识图谱自动推断服务"""

    def __init__(
        self,
        triple_repo: TripleRepository,
        chapter_element_repo: ChapterElementRepository,
        story_node_repo: StoryNodeRepository
    ):
        self.triple_repo = triple_repo
        self.chapter_element_repo = chapter_element_repo
        self.story_node_repo = story_node_repo

    async def infer_from_chapter(self, chapter_id: str) -> List[Triple]:
        """
        从章节推断三元组

        Args:
            chapter_id: 章节 ID

        Returns:
            推断的三元组列表
        """
        # 获取章节信息
        chapter = await self.story_node_repo.get_by_id(chapter_id)
        if not chapter:
            return []

        # 获取章节关联的所有元素
        elements = await self.chapter_element_repo.get_by_chapter(chapter_id)

        # 应用推断规则
        inferred_triples = []

        # 规则 1：人物共同出场 → 认识关系
        inferred_triples.extend(
            await self._infer_character_acquaintance(chapter, elements)
        )

        # 规则 2：POV 人物 + 出场人物 → 互动关系
        inferred_triples.extend(
            await self._infer_character_interaction(chapter, elements)
        )

        # 规则 3：人物在地点出场 → 到访过
        inferred_triples.extend(
            await self._infer_character_location(chapter, elements)
        )

        # 规则 4：人物使用道具 → 使用过
        inferred_triples.extend(
            await self._infer_character_item(chapter, elements)
        )

        # 规则 5：人物涉及组织 → 与...有关
        inferred_triples.extend(
            await self._infer_character_organization(chapter, elements)
        )

        # 规则 6：人物参与事件
        inferred_triples.extend(
            await self._infer_character_event(chapter, elements)
        )

        # 规则 7：事件发生地点
        inferred_triples.extend(
            await self._infer_event_location(chapter, elements)
        )

        # 保存或更新三元组
        for triple in inferred_triples:
            await self._save_or_update_triple(triple)

        return inferred_triples

    async def infer_from_novel(self, novel_id: str) -> Dict[str, int]:
        """
        从整部小说推断三元组

        Args:
            novel_id: 小说 ID

        Returns:
            统计信息
        """
        # 获取所有章节
        chapters = await self.story_node_repo.get_chapters_by_novel(novel_id)

        stats = {
            "total_chapters": len(chapters),
            "inferred_triples": 0,
            "updated_triples": 0
        }

        # 逐章推断
        for chapter in chapters:
            triples = await self.infer_from_chapter(chapter.id)
            stats["inferred_triples"] += len(triples)

        # 全局推断（跨章节分析）
        global_triples = await self._infer_global_patterns(novel_id)
        stats["inferred_triples"] += len(global_triples)

        return stats

    async def _infer_character_acquaintance(
        self,
        chapter,
        elements: List[ChapterElement]
    ) -> List[Triple]:
        """推断人物认识关系（共同出场）"""
        # 获取所有出场的主要和普通人物
        characters = [
            e for e in elements
            if e.element_type == ElementType.CHARACTER
            and e.relation_type == RelationType.APPEARS
            and e.importance in [Importance.MAJOR, Importance.NORMAL]
        ]

        if len(characters) < 2:
            return []

        triples = []
        # 两两组合
        for i, char_a in enumerate(characters):
            for char_b in characters[i + 1:]:
                triple = Triple(
                    id=f"triple-{uuid.uuid4().hex[:8]}",
                    novel_id=chapter.novel_id,
                    subject_type="character",
                    subject_id=char_a.element_id,
                    predicate="认识",
                    object_type="character",
                    object_id=char_b.element_id,
                    confidence=0.6,
                    source_type=SourceType.AUTO_INFERRED,
                    source_chapter_id=chapter.id,
                    first_appearance=chapter.title,
                    related_chapters=[chapter.id]
                )
                triples.append(triple)

        return triples

    async def _infer_character_interaction(
        self,
        chapter,
        elements: List[ChapterElement]
    ) -> List[Triple]:
        """推断人物互动关系（POV 人物 + 出场人物）"""
        if not chapter.pov_character_id:
            return []

        # 获取其他主要出场人物
        other_characters = [
            e for e in elements
            if e.element_type == ElementType.CHARACTER
            and e.relation_type == RelationType.APPEARS
            and e.importance == Importance.MAJOR
            and e.element_id != chapter.pov_character_id
        ]

        triples = []
        for char in other_characters:
            triple = Triple(
                id=f"triple-{uuid.uuid4().hex[:8]}",
                novel_id=chapter.novel_id,
                subject_type="character",
                subject_id=chapter.pov_character_id,
                predicate="互动",
                object_type="character",
                object_id=char.element_id,
                confidence=0.7,
                source_type=SourceType.AUTO_INFERRED,
                source_chapter_id=chapter.id,
                first_appearance=chapter.title,
                related_chapters=[chapter.id]
            )
            triples.append(triple)

        return triples

    async def _infer_character_location(
        self,
        chapter,
        elements: List[ChapterElement]
    ) -> List[Triple]:
        """推断人物-地点关系（人物在地点出场）"""
        # 获取出场人物
        characters = [
            e for e in elements
            if e.element_type == ElementType.CHARACTER
            and e.relation_type == RelationType.APPEARS
        ]

        # 获取场景地点
        locations = [
            e for e in elements
            if e.element_type == ElementType.LOCATION
            and e.relation_type == RelationType.SCENE
        ]

        triples = []
        for char in characters:
            for loc in locations:
                triple = Triple(
                    id=f"triple-{uuid.uuid4().hex[:8]}",
                    novel_id=chapter.novel_id,
                    subject_type="character",
                    subject_id=char.element_id,
                    predicate="到访过",
                    object_type="location",
                    object_id=loc.element_id,
                    confidence=0.9,
                    source_type=SourceType.AUTO_INFERRED,
                    source_chapter_id=chapter.id,
                    first_appearance=chapter.title,
                    related_chapters=[chapter.id]
                )
                triples.append(triple)

        return triples

    async def _infer_character_item(
        self,
        chapter,
        elements: List[ChapterElement]
    ) -> List[Triple]:
        """推断人物-道具关系（人物使用道具）"""
        # 获取出场人物
        characters = [
            e for e in elements
            if e.element_type == ElementType.CHARACTER
            and e.relation_type == RelationType.APPEARS
        ]

        # 获取使用的道具
        items = [
            e for e in elements
            if e.element_type == ElementType.ITEM
            and e.relation_type == RelationType.USES
        ]

        triples = []
        for char in characters:
            for item in items:
                triple = Triple(
                    id=f"triple-{uuid.uuid4().hex[:8]}",
                    novel_id=chapter.novel_id,
                    subject_type="character",
                    subject_id=char.element_id,
                    predicate="使用过",
                    object_type="item",
                    object_id=item.element_id,
                    confidence=0.8,
                    source_type=SourceType.AUTO_INFERRED,
                    source_chapter_id=chapter.id,
                    first_appearance=chapter.title,
                    related_chapters=[chapter.id]
                )
                triples.append(triple)

        return triples

    async def _infer_character_organization(
        self,
        chapter,
        elements: List[ChapterElement]
    ) -> List[Triple]:
        """推断人物-组织关系"""
        characters = [
            e for e in elements
            if e.element_type == ElementType.CHARACTER
            and e.relation_type == RelationType.APPEARS
        ]

        organizations = [
            e for e in elements
            if e.element_type == ElementType.ORGANIZATION
            and e.relation_type == RelationType.INVOLVED
        ]

        triples = []
        for char in characters:
            for org in organizations:
                triple = Triple(
                    id=f"triple-{uuid.uuid4().hex[:8]}",
                    novel_id=chapter.novel_id,
                    subject_type="character",
                    subject_id=char.element_id,
                    predicate="与...有关",
                    object_type="organization",
                    object_id=org.element_id,
                    confidence=0.6,
                    source_type=SourceType.AUTO_INFERRED,
                    source_chapter_id=chapter.id,
                    first_appearance=chapter.title,
                    related_chapters=[chapter.id]
                )
                triples.append(triple)

        return triples

    async def _infer_character_event(
        self,
        chapter,
        elements: List[ChapterElement]
    ) -> List[Triple]:
        """推断人物参与事件"""
        characters = [
            e for e in elements
            if e.element_type == ElementType.CHARACTER
            and e.relation_type == RelationType.APPEARS
        ]

        events = [
            e for e in elements
            if e.element_type == ElementType.EVENT
            and e.relation_type == RelationType.OCCURS
        ]

        triples = []
        for char in characters:
            for event in events:
                triple = Triple(
                    id=f"triple-{uuid.uuid4().hex[:8]}",
                    novel_id=chapter.novel_id,
                    subject_type="character",
                    subject_id=char.element_id,
                    predicate="参与",
                    object_type="event",
                    object_id=event.element_id,
                    confidence=0.9,
                    source_type=SourceType.AUTO_INFERRED,
                    source_chapter_id=chapter.id,
                    first_appearance=chapter.title,
                    related_chapters=[chapter.id]
                )
                triples.append(triple)

        return triples

    async def _infer_event_location(
        self,
        chapter,
        elements: List[ChapterElement]
    ) -> List[Triple]:
        """推断事件发生地点"""
        events = [
            e for e in elements
            if e.element_type == ElementType.EVENT
            and e.relation_type == RelationType.OCCURS
        ]

        locations = [
            e for e in elements
            if e.element_type == ElementType.LOCATION
            and e.relation_type == RelationType.SCENE
        ]

        triples = []
        for event in events:
            for loc in locations:
                triple = Triple(
                    id=f"triple-{uuid.uuid4().hex[:8]}",
                    novel_id=chapter.novel_id,
                    subject_type="event",
                    subject_id=event.element_id,
                    predicate="发生于",
                    object_type="location",
                    object_id=loc.element_id,
                    confidence=1.0,
                    source_type=SourceType.AUTO_INFERRED,
                    source_chapter_id=chapter.id,
                    first_appearance=chapter.title,
                    related_chapters=[chapter.id]
                )
                triples.append(triple)

        return triples

    async def _infer_global_patterns(self, novel_id: str) -> List[Triple]:
        """推断全局模式（跨章节分析）"""
        triples = []

        # 分析人物共同出场频率
        co_appearance_stats = await self._analyze_co_appearance(novel_id)
        for (char_a, char_b), count in co_appearance_stats.items():
            if count >= 3:
                # 升级为"熟悉"关系
                existing = await self.triple_repo.find_by_relation(
                    novel_id, "character", char_a, "认识", "character", char_b
                )
                if existing:
                    existing.predicate = "熟悉"
                    existing.confidence = 0.8
                    await self.triple_repo.update(existing)

        # 分析人物-地点频率
        location_stats = await self._analyze_character_locations(novel_id)
        for (char_id, loc_id), count in location_stats.items():
            if count >= 5:
                # 生成"常驻于"关系
                triple = Triple(
                    id=f"triple-{uuid.uuid4().hex[:8]}",
                    novel_id=novel_id,
                    subject_type="character",
                    subject_id=char_id,
                    predicate="常驻于",
                    object_type="location",
                    object_id=loc_id,
                    confidence=0.8,
                    source_type=SourceType.AUTO_INFERRED
                )
                triples.append(triple)
                await self._save_or_update_triple(triple)

        return triples

    async def _analyze_co_appearance(self, novel_id: str) -> Dict[Tuple[str, str], int]:
        """分析人物共同出场频率"""
        # 这里需要执行 SQL 查询
        # 简化实现：返回空字典
        return {}

    async def _analyze_character_locations(self, novel_id: str) -> Dict[Tuple[str, str], int]:
        """分析人物-地点频率"""
        # 这里需要执行 SQL 查询
        # 简化实现：返回空字典
        return {}

    async def _save_or_update_triple(self, triple: Triple):
        """保存或更新三元组"""
        # 检查是否已存在
        existing = await self.triple_repo.find_by_relation(
            triple.novel_id,
            triple.subject_type,
            triple.subject_id,
            triple.predicate,
            triple.object_type,
            triple.object_id
        )

        if existing:
            # 更新相关章节列表
            if triple.source_chapter_id and triple.source_chapter_id not in existing.related_chapters:
                existing.add_related_chapter(triple.source_chapter_id)

            # 提高置信度
            existing.increase_confidence(0.1)

            await self.triple_repo.update(existing)
        else:
            # 创建新三元组
            await self.triple_repo.save(triple)
