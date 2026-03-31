# domain/novel/entities/__init__.py
from domain.novel.entities.novel import Novel, NovelStage
from domain.novel.entities.chapter import Chapter, ChapterStatus

__all__ = ["Novel", "NovelStage", "Chapter", "ChapterStatus"]
