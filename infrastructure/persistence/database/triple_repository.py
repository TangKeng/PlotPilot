"""
三元组（知识图谱关系）Repository
"""

import sqlite3
import json
from typing import List, Optional
from datetime import datetime

from domain.bible.triple import Triple, SourceType


class TripleRepository:
    """三元组仓储"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def save(self, triple: Triple) -> Triple:
        """保存三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO triples (
                    id, novel_id, subject_type, subject_id, predicate, object_type, object_id,
                    confidence, source_type, source_chapter_id, first_appearance, related_chapters,
                    description, tags, attributes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                triple.id,
                triple.novel_id,
                triple.subject_type,
                triple.subject_id,
                triple.predicate,
                triple.object_type,
                triple.object_id,
                triple.confidence,
                triple.source_type.value,
                triple.source_chapter_id,
                triple.first_appearance,
                json.dumps(triple.related_chapters),
                triple.description,
                json.dumps(triple.tags),
                json.dumps(triple.attributes),
                triple.created_at.isoformat(),
                triple.updated_at.isoformat(),
            ))
            conn.commit()
            return triple
        finally:
            conn.close()

    async def update(self, triple: Triple) -> Triple:
        """更新三元组"""
        triple.updated_at = datetime.now()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE triples SET
                    confidence = ?,
                    source_type = ?,
                    source_chapter_id = ?,
                    first_appearance = ?,
                    related_chapters = ?,
                    description = ?,
                    tags = ?,
                    attributes = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                triple.confidence,
                triple.source_type.value,
                triple.source_chapter_id,
                triple.first_appearance,
                json.dumps(triple.related_chapters),
                triple.description,
                json.dumps(triple.tags),
                json.dumps(triple.attributes),
                triple.updated_at.isoformat(),
                triple.id,
            ))
            conn.commit()
            return triple
        finally:
            conn.close()

    async def save_batch(self, triples: List[Triple]) -> List[Triple]:
        """批量保存三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            for triple in triples:
                cursor.execute("""
                    INSERT OR REPLACE INTO triples (
                        id, novel_id, subject_type, subject_id, predicate, object_type, object_id,
                        confidence, source_type, source_chapter_id, first_appearance, related_chapters,
                        description, tags, attributes,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    triple.id,
                    triple.novel_id,
                    triple.subject_type,
                    triple.subject_id,
                    triple.predicate,
                    triple.object_type,
                    triple.object_id,
                    triple.confidence,
                    triple.source_type.value,
                    triple.source_chapter_id,
                    triple.first_appearance,
                    json.dumps(triple.related_chapters),
                    triple.description,
                    json.dumps(triple.tags),
                    json.dumps(triple.attributes),
                    triple.created_at.isoformat(),
                    triple.updated_at.isoformat(),
                ))
            conn.commit()
            return triples
        finally:
            conn.close()

    async def get_by_id(self, triple_id: str) -> Optional[Triple]:
        """根据 ID 获取三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM triples WHERE id = ?", (triple_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None
        finally:
            conn.close()

    async def get_by_novel(self, novel_id: str) -> List[Triple]:
        """获取小说的所有三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM triples
                WHERE novel_id = ?
                ORDER BY created_at DESC
            """, (novel_id,))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    async def find_by_relation(
        self,
        novel_id: str,
        subject_type: str,
        subject_id: str,
        predicate: str,
        object_type: str,
        object_id: str
    ) -> Optional[Triple]:
        """根据关系查找三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM triples
                WHERE novel_id = ?
                AND subject_type = ? AND subject_id = ?
                AND predicate = ?
                AND object_type = ? AND object_id = ?
            """, (novel_id, subject_type, subject_id, predicate, object_type, object_id))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None
        finally:
            conn.close()

    async def get_by_source_type(
        self,
        novel_id: str,
        source_type: SourceType,
        min_confidence: float = 0.0
    ) -> List[Triple]:
        """根据来源类型获取三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM triples
                WHERE novel_id = ?
                AND source_type = ?
                AND confidence >= ?
                ORDER BY confidence DESC, created_at DESC
            """, (novel_id, source_type.value, min_confidence))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    async def get_by_chapter(self, chapter_id: str) -> List[Triple]:
        """获取章节相关的三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM triples
                WHERE source_chapter_id = ?
                OR related_chapters LIKE ?
                ORDER BY created_at DESC
            """, (chapter_id, f'%"{chapter_id}"%'))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    async def get_by_subject(
        self,
        novel_id: str,
        subject_type: str,
        subject_id: str
    ) -> List[Triple]:
        """获取主体相关的三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM triples
                WHERE novel_id = ?
                AND subject_type = ? AND subject_id = ?
                ORDER BY created_at DESC
            """, (novel_id, subject_type, subject_id))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    async def get_by_object(
        self,
        novel_id: str,
        object_type: str,
        object_id: str
    ) -> List[Triple]:
        """获取客体相关的三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM triples
                WHERE novel_id = ?
                AND object_type = ? AND object_id = ?
                ORDER BY created_at DESC
            """, (novel_id, object_type, object_id))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    async def delete(self, triple_id: str) -> bool:
        """删除三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM triples WHERE id = ?", (triple_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    async def delete_by_novel(self, novel_id: str) -> int:
        """删除小说的所有三元组"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM triples WHERE novel_id = ?", (novel_id,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def _row_to_entity(self, row: sqlite3.Row) -> Triple:
        """将数据库行转换为实体"""
        return Triple(
            id=row["id"],
            novel_id=row["novel_id"],
            subject_type=row["subject_type"],
            subject_id=row["subject_id"],
            predicate=row["predicate"],
            object_type=row["object_type"],
            object_id=row["object_id"],

            confidence=row.get("confidence", 1.0),
            source_type=SourceType(row.get("source_type", "manual")),
            source_chapter_id=row.get("source_chapter_id"),
            first_appearance=row.get("first_appearance"),
            related_chapters=row.get("related_chapters", "[]"),

            description=row.get("description"),
            tags=row.get("tags", "[]"),
            attributes=row.get("attributes", "{}"),

            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
