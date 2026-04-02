import uuid
import logging
from typing import Optional, List
from domain.novel.value_objects.chapter_state import ChapterState
from domain.novel.value_objects.novel_id import NovelId
from domain.bible.entities.character import Character
from domain.bible.value_objects.character_id import CharacterId
from domain.novel.value_objects.foreshadowing import (
    Foreshadowing,
    ForeshadowingStatus,
    ImportanceLevel
)
from domain.bible.repositories.bible_repository import BibleRepository
from domain.novel.repositories.foreshadowing_repository import ForeshadowingRepository
from domain.novel.entities.foreshadowing_registry import ForeshadowingRegistry

logger = logging.getLogger(__name__)


class StateUpdater:
    """状态更新应用服务

    根据 ChapterState 更新各个领域对象
    """

    def __init__(
        self,
        bible_repository: BibleRepository,
        foreshadowing_repository: ForeshadowingRepository,
        knowledge_service=None
    ):
        self.bible_repository = bible_repository
        self.foreshadowing_repository = foreshadowing_repository
        self.knowledge_service = knowledge_service

    def update_from_chapter(
        self,
        novel_id: str,
        chapter_number: int,
        chapter_state: ChapterState
    ) -> None:
        """从章节状态更新所有相关对象

        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            chapter_state: 章节状态
        """
        novel_id_obj = NovelId(novel_id)
        logger.info(
            f"StateUpdater.update_from_chapter: novel={novel_id}, chapter={chapter_number}, "
            f"new_characters={len(chapter_state.new_characters)}, "
            f"foreshadowing_planted={len(chapter_state.foreshadowing_planted)}, "
            f"foreshadowing_resolved={len(chapter_state.foreshadowing_resolved)}"
        )

        # 更新 Bible（新角色）
        if chapter_state.has_new_characters():
            logger.debug(f"Updating Bible with {len(chapter_state.new_characters)} new characters")
            bible = self.bible_repository.get_by_novel_id(novel_id_obj)
            if bible is None:
                logger.warning(f"Bible not found for novel {novel_id}, skipping character update")
            else:
                for char_data in chapter_state.new_characters:
                    char_id = CharacterId(str(uuid.uuid4()))
                    character = Character(
                        id=char_id,
                        name=char_data.get("name", "未知角色"),
                        description=char_data.get("description", "")
                    )
                    bible.add_character(character)
                    logger.debug(f"Added character: {char_data.get('name')}")

                self.bible_repository.save(bible)
                logger.info(f"Bible updated: added {len(chapter_state.new_characters)} new characters for novel {novel_id}")
        else:
            logger.debug("No new characters to add")

        # 更新 ForeshadowingRegistry（新伏笔和解决伏笔）
        if chapter_state.has_foreshadowing_activity():
            logger.debug(
                f"Updating ForeshadowingRegistry: "
                f"plant={len(chapter_state.foreshadowing_planted)}, "
                f"resolve={len(chapter_state.foreshadowing_resolved)}"
            )
            foreshadowing_registry = self.foreshadowing_repository.get_by_novel_id(novel_id_obj)
            if foreshadowing_registry is None:
                logger.info(f"ForeshadowingRegistry not found for novel {novel_id}, creating new one")
                foreshadowing_registry = ForeshadowingRegistry(
                    id=str(uuid.uuid4()),
                    novel_id=novel_id_obj
                )

            # 添加新伏笔
            for foreshadow_data in chapter_state.foreshadowing_planted:
                foreshadowing = Foreshadowing(
                    id=str(uuid.uuid4()),
                    planted_in_chapter=foreshadow_data.get("chapter", chapter_number),
                    description=foreshadow_data.get("description", ""),
                    importance=ImportanceLevel.MEDIUM,
                    status=ForeshadowingStatus.PLANTED
                )
                foreshadowing_registry.register(foreshadowing)
                logger.debug(f"Planted foreshadowing: {foreshadow_data.get('description', '')[:50]}")

            # 解决伏笔
            for resolved_data in chapter_state.foreshadowing_resolved:
                fid = resolved_data.get("foreshadowing_id", "")
                resolved_ch = resolved_data.get("chapter", chapter_number)
                try:
                    foreshadowing_registry.mark_resolved(
                        foreshadowing_id=fid,
                        resolved_in_chapter=resolved_ch
                    )
                    logger.debug(f"Resolved foreshadowing: {fid}")
                except Exception as e:
                    logger.warning(f"Failed to resolve foreshadowing {fid}: {e}")

            self.foreshadowing_repository.save(foreshadowing_registry)
            logger.info(f"ForeshadowingRegistry updated for novel {novel_id}")
        else:
            logger.debug("No foreshadowing activity to update")

        # 更新 Knowledge（章节摘要）
        if self.knowledge_service:
            self._update_knowledge(novel_id, chapter_number, chapter_state)

    def _update_knowledge(
        self,
        novel_id: str,
        chapter_number: int,
        chapter_state: ChapterState
    ) -> None:
        """更新 Knowledge 中的章节摘要和知识三元组

        Args:
            novel_id: 小说 ID
            chapter_number: 章节号
            chapter_state: 章节状态
        """
        try:
            # 构建关键事件描述
            events_desc = ""
            if chapter_state.events:
                event_texts = [e.get("description", "") for e in chapter_state.events[:5]]
                events_desc = "；".join(t for t in event_texts if t)

            # 构建新角色描述
            new_chars_desc = ""
            if chapter_state.new_characters:
                new_chars_desc = "新登场：" + "、".join(
                    c.get("name", "") for c in chapter_state.new_characters
                )

            key_events = events_desc or new_chars_desc or "（本章无特殊标注事件）"

            # 构建未解伏笔描述
            open_threads = ""
            if chapter_state.foreshadowing_planted:
                threads = [f.get("description", "")[:40] for f in chapter_state.foreshadowing_planted]
                open_threads = "伏笔：" + "；".join(t for t in threads if t)

            self.knowledge_service.upsert_chapter_summary(
                novel_id=novel_id,
                chapter_id=chapter_number,
                summary="",  # 暂不生成摘要文字（节省 token）
                key_events=key_events,
                open_threads=open_threads,
                consistency_note="",
                beat_sections=[],
                sync_status="auto"
            )
            logger.info(f"Knowledge chapter summary updated for novel {novel_id}, chapter {chapter_number}")

            # 如有新角色，添加为知识三元组
            for char_data in chapter_state.new_characters:
                char_name = char_data.get("name", "")
                char_desc = char_data.get("description", "")
                if char_name and char_desc:
                    fact_id = f"char-{novel_id}-{char_name}-ch{chapter_number}"
                    self.knowledge_service.upsert_fact(
                        novel_id=novel_id,
                        fact_id=fact_id,
                        subject=char_name,
                        predicate="登场于",
                        object=f"第{chapter_number}章",
                        chapter_id=chapter_number,
                        note=char_desc[:100]
                    )
        except Exception as e:
            logger.warning(f"Failed to update Knowledge for novel {novel_id}: {e}")
