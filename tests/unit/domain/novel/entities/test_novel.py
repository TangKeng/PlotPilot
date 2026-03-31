# tests/unit/domain/novel/entities/test_novel.py
import pytest
from domain.novel.entities.novel import Novel, NovelStage
from domain.novel.entities.chapter import Chapter
from domain.novel.value_objects.novel_id import NovelId
from domain.shared.exceptions import InvalidOperationError


def test_novel_creation():
    """测试创建小说"""
    novel = Novel(
        id=NovelId("novel-1"),
        title="测试小说",
        author="测试作者",
        target_chapters=10
    )
    assert novel.id.value == "novel-1"
    assert novel.title == "测试小说"
    assert novel.stage == NovelStage.PLANNING


def test_novel_add_chapter():
    """测试添加章节"""
    novel = Novel(
        id=NovelId("novel-1"),
        title="测试小说",
        author="测试作者",
        target_chapters=10
    )
    chapter = Chapter(
        id="chapter-1",
        novel_id=NovelId("novel-1"),
        number=1,
        title="第一章"
    )
    novel.add_chapter(chapter)
    assert len(novel.chapters) == 1
    assert novel.chapters[0].number == 1


def test_novel_add_chapter_non_sequential_raises_error():
    """测试添加非连续章节抛出异常"""
    novel = Novel(
        id=NovelId("novel-1"),
        title="测试小说",
        author="测试作者",
        target_chapters=10
    )
    chapter1 = Chapter(
        id="chapter-1",
        novel_id=NovelId("novel-1"),
        number=1,
        title="第一章"
    )
    chapter3 = Chapter(
        id="chapter-3",
        novel_id=NovelId("novel-1"),
        number=3,
        title="第三章"
    )
    novel.add_chapter(chapter1)

    with pytest.raises(InvalidOperationError):
        novel.add_chapter(chapter3)  # 跳过第2章
