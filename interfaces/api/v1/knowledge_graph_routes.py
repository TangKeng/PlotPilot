"""
知识图谱推断 API 路由
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from application.services.knowledge_graph_service import KnowledgeGraphService
from infrastructure.persistence.database.triple_repository import TripleRepository
from infrastructure.persistence.database.chapter_element_repository import ChapterElementRepository
from infrastructure.persistence.database.story_node_repository import StoryNodeRepository
from application.paths import get_db_path
from domain.bible.triple import SourceType


router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["knowledge-graph"])


# ==================== 依赖注入 ====================

def get_kg_service() -> KnowledgeGraphService:
    """获取知识图谱服务"""
    db_path = get_db_path()
    return KnowledgeGraphService(
        TripleRepository(db_path),
        ChapterElementRepository(db_path),
        StoryNodeRepository(db_path)
    )


def get_triple_repo() -> TripleRepository:
    """获取三元组仓储"""
    return TripleRepository(get_db_path())


# ==================== API 端点 ====================

@router.post("/novels/{novel_id}/infer")
async def infer_novel_knowledge_graph(
    novel_id: str,
    service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    推断整部小说的知识图谱

    分析所有章节的元素关联，自动生成三元组关系。
    这是一个耗时操作，建议在后台执行。
    """
    try:
        stats = await service.infer_from_novel(novel_id)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推断知识图谱失败: {str(e)}")


@router.post("/chapters/{chapter_id}/infer")
async def infer_chapter_knowledge_graph(
    chapter_id: str,
    service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    推断单个章节的知识图谱

    分析章节的元素关联，自动生成三元组关系。
    """
    try:
        triples = await service.infer_from_chapter(chapter_id)

        return {
            "success": True,
            "data": {
                "chapter_id": chapter_id,
                "inferred_triples": len(triples),
                "triples": [triple.to_dict() for triple in triples]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推断章节知识图谱失败: {str(e)}")


@router.get("/novels/{novel_id}/triples")
async def get_novel_triples(
    novel_id: str,
    source_type: Optional[str] = None,
    min_confidence: float = 0.0,
    repo: TripleRepository = Depends(get_triple_repo)
):
    """
    获取小说的所有三元组

    可选参数：
    - source_type: 过滤来源类型 (manual/auto_inferred/ai_generated)
    - min_confidence: 最低置信度阈值 (0.0-1.0)
    """
    try:
        if source_type:
            triples = await repo.get_by_source_type(
                novel_id,
                SourceType(source_type),
                min_confidence
            )
        else:
            triples = await repo.get_by_novel(novel_id)
            # 过滤置信度
            triples = [t for t in triples if t.confidence >= min_confidence]

        return {
            "success": True,
            "data": {
                "total": len(triples),
                "triples": [triple.to_dict() for triple in triples]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取三元组失败: {str(e)}")


@router.get("/chapters/{chapter_id}/triples")
async def get_chapter_triples(
    chapter_id: str,
    repo: TripleRepository = Depends(get_triple_repo)
):
    """
    获取章节相关的三元组

    返回该章节推断出的所有三元组。
    """
    try:
        triples = await repo.get_by_chapter(chapter_id)

        return {
            "success": True,
            "data": {
                "chapter_id": chapter_id,
                "total": len(triples),
                "triples": [triple.to_dict() for triple in triples]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取章节三元组失败: {str(e)}")


@router.post("/triples/{triple_id}/confirm")
async def confirm_triple(
    triple_id: str,
    repo: TripleRepository = Depends(get_triple_repo)
):
    """
    确认三元组

    将自动推断的三元组确认为手动创建，置信度设为 1.0。
    """
    try:
        triple = await repo.get_by_id(triple_id)
        if not triple:
            raise HTTPException(status_code=404, detail="三元组不存在")

        triple.confirm()
        await repo.update(triple)

        return {
            "success": True,
            "data": triple.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"确认三元组失败: {str(e)}")


@router.delete("/triples/{triple_id}")
async def delete_triple(
    triple_id: str,
    repo: TripleRepository = Depends(get_triple_repo)
):
    """
    删除三元组

    用于拒绝自动推断的错误关系。
    """
    try:
        success = await repo.delete(triple_id)

        if not success:
            raise HTTPException(status_code=404, detail="三元组不存在")

        return {
            "success": True,
            "message": "删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除三元组失败: {str(e)}")


@router.get("/elements/{element_type}/{element_id}/relations")
async def get_element_relations(
    element_type: str,
    element_id: str,
    repo: TripleRepository = Depends(get_triple_repo)
):
    """
    获取元素的所有关系

    查询某个元素（人物、地点等）的所有三元组关系。
    包括作为主体和客体的关系。
    """
    try:
        # 获取作为主体的关系
        subject_triples = await repo.get_by_subject(
            novel_id="",  # 需要从元素 ID 推断
            subject_type=element_type,
            subject_id=element_id
        )

        # 获取作为客体的关系
        object_triples = await repo.get_by_object(
            novel_id="",  # 需要从元素 ID 推断
            object_type=element_type,
            object_id=element_id
        )

        return {
            "success": True,
            "data": {
                "element_type": element_type,
                "element_id": element_id,
                "as_subject": [t.to_dict() for t in subject_triples],
                "as_object": [t.to_dict() for t in object_triples],
                "total": len(subject_triples) + len(object_triples)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取元素关系失败: {str(e)}")


@router.get("/novels/{novel_id}/statistics")
async def get_knowledge_graph_statistics(
    novel_id: str,
    repo: TripleRepository = Depends(get_triple_repo)
):
    """
    获取知识图谱统计信息

    返回三元组的统计数据，包括总数、来源分布、置信度分布等。
    """
    try:
        all_triples = await repo.get_by_novel(novel_id)

        # 统计来源类型
        source_stats = {}
        for triple in all_triples:
            source = triple.source_type.value
            source_stats[source] = source_stats.get(source, 0) + 1

        # 统计置信度分布
        confidence_ranges = {
            "high": 0,      # >= 0.8
            "medium": 0,    # 0.6 - 0.8
            "low": 0        # < 0.6
        }
        for triple in all_triples:
            if triple.confidence >= 0.8:
                confidence_ranges["high"] += 1
            elif triple.confidence >= 0.6:
                confidence_ranges["medium"] += 1
            else:
                confidence_ranges["low"] += 1

        # 统计关系类型
        predicate_stats = {}
        for triple in all_triples:
            pred = triple.predicate
            predicate_stats[pred] = predicate_stats.get(pred, 0) + 1

        return {
            "success": True,
            "data": {
                "total_triples": len(all_triples),
                "source_distribution": source_stats,
                "confidence_distribution": confidence_ranges,
                "predicate_distribution": predicate_stats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
